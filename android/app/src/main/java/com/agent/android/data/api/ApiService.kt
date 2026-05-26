package com.agent.android.data.api

import com.agent.android.data.model.ApiResponse
import com.agent.android.data.model.ChatData
import com.agent.android.data.model.ChatRequest
import com.agent.android.data.model.StopRequest
import com.agent.android.data.model.UploadData
import okhttp3.MultipartBody
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.Multipart
import retrofit2.http.POST
import retrofit2.http.Part

interface ApiService {

    @Multipart
    @POST("api/v1/upload/image")
    suspend fun uploadImage(@Part file: MultipartBody.Part): ApiResponse<UploadData>

    @POST("api/v1/chat")
    suspend fun createChat(@Body request: ChatRequest): ApiResponse<ChatData>

    @POST("api/v1/chat/stop")
    suspend fun stopChat(@Body request: StopRequest): ApiResponse<Unit>

    @GET("api/v1/health")
    suspend fun healthCheck(): ApiResponse<Unit>
}
