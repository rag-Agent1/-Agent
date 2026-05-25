package com.agent.android.data.api

import com.google.gson.Gson
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import java.util.concurrent.TimeUnit

object RetrofitClient {

    private var baseUrl: String = DEFAULT_BASE_URL
    private var retrofit: Retrofit? = null
    private var apiService: ApiService? = null

    val okHttpClient: OkHttpClient by lazy {
        val logging = HttpLoggingInterceptor().apply {
            level = HttpLoggingInterceptor.Level.BODY
        }
        OkHttpClient.Builder()
            .addInterceptor(logging)
            .connectTimeout(15, TimeUnit.SECONDS)
            .readTimeout(30, TimeUnit.SECONDS)
            .writeTimeout(30, TimeUnit.SECONDS)
            .build()
    }

    fun getApiService(): ApiService {
        val current = apiService
        if (current != null) return current
        return createService()
    }

    fun updateBaseUrl(url: String) {
        if (url != baseUrl) {
            baseUrl = url.trimEnd('/') + "/"
            retrofit = null
            apiService = null
        }
    }

    fun getBaseUrl(): String = baseUrl

    private fun createService(): ApiService {
        val retrofit = Retrofit.Builder()
            .baseUrl(baseUrl)
            .client(okHttpClient)
            .addConverterFactory(GsonConverterFactory.create(Gson()))
            .build()
        this.retrofit = retrofit
        val service = retrofit.create(ApiService::class.java)
        apiService = service
        return service
    }

    private const val DEFAULT_BASE_URL = "http://10.0.2.2:8000/"
}
