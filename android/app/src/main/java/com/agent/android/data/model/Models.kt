package com.agent.android.data.model

import com.google.gson.annotations.SerializedName

// ---------- API 通用响应包装 ----------

data class ApiResponse<T>(
    val code: Int,
    val message: String,
    val data: T? = null
)

data class ApiError(
    val code: String,
    val message: String
)

// ---------- 上传图片 ----------

data class UploadData(
    @SerializedName("image_id") val imageId: String,
    val url: String,
    val width: Int,
    val height: Int,
    val size: Long
)

// ---------- 发起会话 ----------

data class ChatRequest(
    @SerializedName("session_id") val sessionId: String?,
    @SerializedName("image_id") val imageId: String,
    val text: String? = null
)

data class ChatData(
    @SerializedName("session_id") val sessionId: String,
    @SerializedName("message_id") val messageId: String,
    @SerializedName("stream_url") val streamUrl: String
)

// ---------- 中断 ----------

data class StopRequest(
    @SerializedName("message_id") val messageId: String
)

// ---------- SSE 事件体 ----------

data class CandidatesEvent(
    val candidates: List<Candidate>
)

data class DeltaTextEvent(
    val text: String
)

data class CitationsEvent(
    val citations: List<Citation>
)

data class UsageInfo(
    @SerializedName("total_tokens") val totalTokens: Int?,
    @SerializedName("prompt_tokens") val promptTokens: Int?,
    @SerializedName("completion_tokens") val completionTokens: Int?
)

data class FinalEvent(
    @SerializedName("need_clarify") val needClarify: Boolean,
    @SerializedName("clarify_question") val clarifyQuestion: String?,
    val usage: UsageInfo? = null
)

// ---------- 核心业务模型 ----------

data class Candidate(
    @SerializedName("sku_id") val skuId: String,
    val score: Double,
    val title: String,
    @SerializedName("image_url") val imageUrl: String,
    val attrs: Map<String, String>? = null,
    val price: Double? = null
)

data class Citation(
    @SerializedName("sku_id") val skuId: String,
    @SerializedName("chunk_id") val chunkId: String,
    val snippet: String,
    val source: String
)

// ---------- SSE 事件密封类 ----------

sealed class SseEvent {
    data class Candidates(val candidates: List<Candidate>) : SseEvent()
    data class DeltaText(val text: String) : SseEvent()
    data class Citations(val citations: List<Citation>) : SseEvent()
    data class Final(val event: FinalEvent) : SseEvent()
    data class Error(val message: String) : SseEvent()
}

// ---------- UI 聊天消息模型 ----------

data class ChatMessage(
    val id: String,
    val role: MessageRole,
    val text: String = "",
    val imageUrl: String? = null,
    val imageLocalUri: String? = null,
    val candidates: List<Candidate>? = null,
    val citations: List<Citation>? = null,
    val needClarify: Boolean = false,
    val clarifyQuestion: String? = null,
    val isLoading: Boolean = false,
    val isStreaming: Boolean = false,
    val isError: Boolean = false,
    val errorMessage: String? = null
)

enum class MessageRole { USER, ASSISTANT }

// ---------- 连接状态 ----------

enum class ConnectionStatus {
    CONNECTED, DISCONNECTED, CHECKING
}
