package com.agent.android.data.repository

import com.agent.android.data.api.RetrofitClient
import com.agent.android.data.api.SseClient
import com.agent.android.data.model.ChatRequest
import com.agent.android.data.model.SseEvent
import com.agent.android.data.model.StopRequest
import com.agent.android.data.model.UploadData
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.MultipartBody
import okhttp3.RequestBody.Companion.toRequestBody

class ChatRepository {

    private val api get() = RetrofitClient.getApiService()

    suspend fun uploadImage(imageBytes: ByteArray, fileName: String = "image.jpg"): Result<UploadData> {
        return withContext(Dispatchers.IO) {
            try {
                val mediaType = "image/jpeg".toMediaTypeOrNull()
                val requestBody = imageBytes.toRequestBody(mediaType)
                val part = MultipartBody.Part.createFormData("file", fileName, requestBody)
                val response = api.uploadImage(part)
                if (response.code == 0 && response.data != null) {
                    Result.success(response.data)
                } else {
                    Result.failure(Exception(response.message))
                }
            } catch (e: Exception) {
                Result.failure(e)
            }
        }
    }

    suspend fun createChat(
        sessionId: String?,
        imageId: String,
        text: String?
    ): Result<ChatSessionInfo> {
        return withContext(Dispatchers.IO) {
            try {
                val request = ChatRequest(
                    sessionId = sessionId,
                    imageId = imageId,
                    text = text
                )
                val response = api.createChat(request)
                if (response.code == 0 && response.data != null) {
                    Result.success(
                        ChatSessionInfo(
                            sessionId = response.data.sessionId,
                            messageId = response.data.messageId,
                            streamUrl = response.data.streamUrl
                        )
                    )
                } else {
                    Result.failure(Exception(response.message))
                }
            } catch (e: Exception) {
                Result.failure(e)
            }
        }
    }

    fun connectStream(streamUrl: String): Flow<SseEvent> {
        val client = SseClient()
        return client.connect(streamUrl)
    }

    suspend fun stopChat(messageId: String): Result<Unit> {
        return withContext(Dispatchers.IO) {
            try {
                val response = api.stopChat(StopRequest(messageId))
                if (response.code == 0) {
                    Result.success(Unit)
                } else {
                    Result.failure(Exception(response.message))
                }
            } catch (e: Exception) {
                Result.failure(e)
            }
        }
    }

    suspend fun healthCheck(): Result<Unit> {
        return withContext(Dispatchers.IO) {
            try {
                val response = api.healthCheck()
                if (response.code == 0) {
                    Result.success(Unit)
                } else {
                    Result.failure(Exception(response.message))
                }
            } catch (e: Exception) {
                Result.failure(e)
            }
        }
    }
}

data class ChatSessionInfo(
    val sessionId: String,
    val messageId: String,
    val streamUrl: String
)
