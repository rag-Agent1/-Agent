package com.agent.android.viewmodel

import android.content.Context
import android.net.Uri
import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.agent.android.data.ImageCompressor
import com.agent.android.data.SessionManager
import com.agent.android.data.api.RetrofitClient
import com.agent.android.data.model.Candidate
import com.agent.android.data.model.ChatMessage
import com.agent.android.data.model.Citation
import com.agent.android.data.model.ConnectionStatus
import com.agent.android.data.model.MessageRole
import com.agent.android.data.model.SseEvent
import com.agent.android.data.repository.ChatRepository
import com.agent.android.data.repository.ChatSessionInfo
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.withContext
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.catch
import kotlinx.coroutines.flow.onCompletion
import kotlinx.coroutines.launch

data class ChatUiState(
    val messages: List<ChatMessage> = emptyList(),
    val isStreaming: Boolean = false,
    val currentStreamingMessageId: String? = null,
    val isUploading: Boolean = false,
    val uploadProgress: Float = 0f,
    val error: String? = null,
    val connectionStatus: ConnectionStatus = ConnectionStatus.CHECKING,
    val selectedImageUri: Uri? = null
)

class ChatViewModel(
    private val repository: ChatRepository = ChatRepository(),
    private val sessionManager: SessionManager? = null
) : ViewModel() {

    private val _uiState = MutableStateFlow(ChatUiState())
    val uiState: StateFlow<ChatUiState> = _uiState.asStateFlow()

    private var sessionId: String? = null
    private var currentImageId: String? = null
    private var streamJob: Job? = null
    private var messageCounter = 0

    // 重试用：保存上一次发送的参数
    private var lastSendImageUri: Uri? = null
    private var lastSendText: String? = null
    private var userStopped = false

    init {
        checkHealth()
        viewModelScope.launch {
            sessionManager?.getSessionId()?.let { id ->
                sessionId = id
            }
        }
        // 每 30 秒自动检查后端连接状态
        viewModelScope.launch {
            while (true) {
                kotlinx.coroutines.delay(30_000)
                checkHealth()
            }
        }
    }

    // ---------- 健康检查 ----------

    fun checkHealth() {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(connectionStatus = ConnectionStatus.CHECKING)
            val result = repository.healthCheck()
            _uiState.value = _uiState.value.copy(
                connectionStatus = if (result.isSuccess) {
                    ConnectionStatus.CONNECTED
                } else {
                    ConnectionStatus.DISCONNECTED
                }
            )
        }
    }

    // ---------- 图片选择 ----------

    fun onImageSelected(uri: Uri) {
        _uiState.value = _uiState.value.copy(selectedImageUri = uri)
    }

    fun clearSelectedImage() {
        _uiState.value = _uiState.value.copy(selectedImageUri = null)
    }

    // ---------- 发送消息 ----------

    fun sendMessage(context: Context, text: String? = null) {
        val imageUri = _uiState.value.selectedImageUri
        lastSendImageUri = imageUri
        lastSendText = text
        if (imageUri == null) {
            // 仅文字，不发送图片
            if (text.isNullOrBlank()) return
            sendTextOnly(text)
            return
        }

        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isUploading = true)

            try {
                // 1. 压缩图片（切到 IO 线程，避免大图 OOM 崩溃）
                val compressedBytes = withContext(Dispatchers.IO) {
                    ImageCompressor.compress(context, imageUri)
                }
                val fileName = "image_${System.currentTimeMillis()}.jpg"

                // 2. 上传图片
                val uploadResult = repository.uploadImage(compressedBytes, fileName)
                if (uploadResult.isFailure) {
                    val errMsg = uploadResult.exceptionOrNull()?.message ?: ""
                    val friendly = when {
                        errMsg.contains("timeout", ignoreCase = true) -> "图片上传超时，请检查网络后重试"
                        errMsg.contains("refused", ignoreCase = true) ||
                        errMsg.contains("Failed to connect", ignoreCase = true) ||
                        errMsg.contains("Unable to resolve host", ignoreCase = true) -> "无法连接到服务器，请确认后端已启动"
                        else -> "图片上传失败，请重试"
                    }
                    _uiState.value = _uiState.value.copy(
                        isUploading = false,
                        error = friendly,
                        connectionStatus = ConnectionStatus.DISCONNECTED
                    )
                    return@launch
                }

                val uploadData = uploadResult.getOrNull() ?: return@launch
                currentImageId = uploadData.imageId

                // 3. 添加用户消息
                addUserMessage(text, imageUri.toString())

                _uiState.value = _uiState.value.copy(
                    isUploading = false,
                    selectedImageUri = null,
                    connectionStatus = ConnectionStatus.CONNECTED
                )

                // 4. 发起会话
                startChat(text)

            } catch (e: Throwable) {
                val friendly = when {
                    e.message?.contains("Unable to decode", ignoreCase = true) == true -> "图片格式不支持，请选择 jpg/png 格式"
                    e.message?.contains("openInputStream", ignoreCase = true) == true -> "无法读取图片，请重新选择"
                    else -> "处理图片失败，请重试"
                }
                _uiState.value = _uiState.value.copy(
                    isUploading = false,
                    error = friendly
                )
            }
        }
    }

    // ---------- 停止生成 ----------

    fun stopGeneration() {
        userStopped = true
        streamJob?.cancel()
        val messageId = _uiState.value.currentStreamingMessageId
        // 从列表中移除这次对话（用户消息 + AI 消息），像没发生过一样
        val msgs = _uiState.value.messages
        val streamingIdx = msgs.indexOfLast { it.isStreaming }
        val newMsgs = if (streamingIdx >= 1) {
            msgs.toMutableList().apply {
                removeAt(streamingIdx)     // 移除 AI 消息
                if (getOrNull(streamingIdx - 1)?.role == MessageRole.USER) {
                    removeAt(streamingIdx - 1) // 移除对应的用户消息
                }
            }
        } else if (streamingIdx >= 0) {
            msgs.toMutableList().apply { removeAt(streamingIdx) }
        } else {
            msgs
        }
        // 把图片放回待发送区，方便重新发
        _uiState.value = _uiState.value.copy(
            selectedImageUri = lastSendImageUri,
            messages = newMsgs,
            isStreaming = false,
            currentStreamingMessageId = null
        )
        // 通知后端中断
        if (messageId != null) {
            viewModelScope.launch {
                repository.stopChat(messageId)
            }
        }
    }

    // ---------- 澄清回复 ----------

    fun sendClarification(text: String) {
        addUserMessage(text)
        startChat(text)
    }

    // ---------- 清除错误 ----------

    fun clearError() {
        _uiState.value = _uiState.value.copy(error = null)
    }

    // ---------- 重试 ----------

    fun retryLastMessage(context: Context) {
        val uri = lastSendImageUri ?: return
        _uiState.value = _uiState.value.copy(error = null)
        // 重新设置图片并发送
        _uiState.value = _uiState.value.copy(selectedImageUri = uri)
        sendMessage(context, lastSendText)
    }

    // ---------- 新会话 ----------

    fun newSession() {
        userStopped = false
        streamJob?.cancel()
        sessionId = null
        currentImageId = null
        messageCounter = 0
        viewModelScope.launch {
            sessionManager?.clearSession()
        }
        _uiState.value = ChatUiState(
            connectionStatus = _uiState.value.connectionStatus
        )
    }

    // ---------- 内部方法 ----------

    private fun sendTextOnly(text: String) {
        if (text.isBlank()) return

        // 先添加用户消息
        addUserMessage(text)

        // 如果没有 image_id，则取最后一条有图片的消息的 image_id
        if (currentImageId == null) {
            // 查找最近的消息中是否有图片
            val lastImageMsg = _uiState.value.messages.lastOrNull {
                it.role == MessageRole.USER && (it.imageUrl != null || it.imageLocalUri != null)
            }
            _uiState.value = _uiState.value.copy(
                error = if (lastImageMsg == null) "请先拍照或选择一张图片再提问" else null
            )
            if (lastImageMsg == null) return
        }

        startChat(text)
    }

    private fun startChat(text: String? = null) {
        val imageId = currentImageId ?: return

        val assistantMessage = ChatMessage(
            id = "msg_${++messageCounter}",
            role = MessageRole.ASSISTANT,
            isLoading = true,
            isStreaming = true
        )

        _uiState.value = _uiState.value.copy(
            messages = _uiState.value.messages + assistantMessage,
            isStreaming = true,
            currentStreamingMessageId = assistantMessage.id,
            error = null
        )

        streamJob = viewModelScope.launch {
            val chatResult = repository.createChat(sessionId, imageId, text)
            if (chatResult.isFailure) {
                updateStreamingError(chatResult.exceptionOrNull()?.message ?: "请求失败")
                return@launch
            }

            val info = chatResult.getOrNull() ?: return@launch
            sessionId = info.sessionId
            sessionManager?.saveSessionId(info.sessionId)

            // 连接 SSE 流
            userStopped = false
            repository.connectStream(info.streamUrl)
                .onCompletion { cause ->
                    if (cause != null && !userStopped) {
                        val errMsg = cause.message ?: ""
                        val msg = when {
                            errMsg.contains("timeout", ignoreCase = true) -> "网络连接超时，请检查后端服务"
                            errMsg.contains("refused", ignoreCase = true) ||
                            errMsg.contains("Failed to connect", ignoreCase = true) ||
                            errMsg.contains("Unable to resolve host", ignoreCase = true) -> "无法连接到服务器，请确认后端已启动"
                            errMsg.contains("Cancel", ignoreCase = true) -> "已停止生成"
                            else -> "网络连接已断开，请检查后端服务"
                        }
                        if (msg != "已停止生成") {
                            updateStreamingError(msg)
                            _uiState.value = _uiState.value.copy(connectionStatus = ConnectionStatus.DISCONNECTED)
                        }
                    }
                }
                .catch { e ->
                    if (!userStopped) {
                        val errMsg = e.message ?: ""
                        val msg = when {
                            errMsg.contains("timeout", ignoreCase = true) -> "网络连接超时，请检查后端服务"
                            errMsg.contains("refused", ignoreCase = true) ||
                            errMsg.contains("Failed to connect", ignoreCase = true) ||
                            errMsg.contains("Unable to resolve host", ignoreCase = true) -> "无法连接到服务器，请确认后端已启动"
                            else -> "服务器出错了，请稍后重试"
                        }
                        updateStreamingError(msg)
                    }
                }
                .collect { event ->
                    handleSseEvent(event, info)
                }
        }
    }

    private fun handleSseEvent(event: SseEvent, info: ChatSessionInfo) {
        when (event) {
            is SseEvent.Candidates -> {
                updateAssistantMessage { it.copy(candidates = event.candidates) }
            }
            is SseEvent.DeltaText -> {
                val msgs = _uiState.value.messages
                val idx = msgs.indexOfLast { it.id == info.messageId || it.isStreaming }
                if (idx >= 0) {
                    val current = msgs[idx]
                    val updated = current.copy(
                        text = current.text + event.text,
                        isLoading = false
                    )
                    val newMsgs = msgs.toMutableList().apply { set(idx, updated) }
                    _uiState.value = _uiState.value.copy(messages = newMsgs)
                }
            }
            is SseEvent.Citations -> {
                updateAssistantMessage { it.copy(citations = event.citations) }
            }
            is SseEvent.Final -> {
                val finalEvent = event.event
                updateAssistantMessage { msg ->
                    msg.copy(
                        isStreaming = false,
                        isLoading = false,
                        needClarify = finalEvent.needClarify,
                        clarifyQuestion = finalEvent.clarifyQuestion
                    )
                }
                _uiState.value = _uiState.value.copy(
                    isStreaming = false,
                    currentStreamingMessageId = null
                )
                streamJob = null
            }
            is SseEvent.Error -> {
                updateStreamingError(event.message)
            }
        }
    }

    private fun addUserMessage(text: String?, imageUri: String? = null) {
        val msg = ChatMessage(
            id = "msg_${++messageCounter}",
            role = MessageRole.USER,
            text = text ?: "",
            imageUrl = imageUri,
            imageLocalUri = imageUri
        )
        _uiState.value = _uiState.value.copy(
            messages = _uiState.value.messages + msg
        )
    }

    private fun updateStreamingError(errorMsg: String) {
        updateAssistantMessage { it.copy(isStreaming = false, isLoading = false, isError = true, errorMessage = errorMsg) }
        _uiState.value = _uiState.value.copy(isStreaming = false, currentStreamingMessageId = null, error = errorMsg)
        streamJob = null
    }

    private fun updateAssistantMessage(transform: (ChatMessage) -> ChatMessage) {
        val msgs = _uiState.value.messages
        val idx = msgs.indexOfLast { it.isStreaming || it.id == _uiState.value.currentStreamingMessageId }
        if (idx >= 0) {
            val updated = transform(msgs[idx])
            val newMsgs = msgs.toMutableList().apply { set(idx, updated) }
            _uiState.value = _uiState.value.copy(messages = newMsgs)
        }
    }

    // ---------- Factory ----------

    class Factory(
        private val sessionManager: SessionManager? = null
    ) : ViewModelProvider.Factory {
        @Suppress("UNCHECKED_CAST")
        override fun <T : ViewModel> create(modelClass: Class<T>): T {
            return ChatViewModel(sessionManager = sessionManager) as T
        }
    }
}
