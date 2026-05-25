package com.agent.android.data.api

import com.agent.android.data.model.Candidate
import com.agent.android.data.model.Citation
import com.agent.android.data.model.FinalEvent
import com.agent.android.data.model.SseEvent
import com.google.gson.Gson
import com.google.gson.JsonObject
import kotlinx.coroutines.channels.awaitClose
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.callbackFlow
import okhttp3.Request
import okhttp3.Response
import okhttp3.sse.EventSource
import okhttp3.sse.EventSourceListener
import okhttp3.sse.EventSources

class SseClient {

    private val gson = Gson()
    private var eventSource: EventSource? = null

    fun connect(streamUrl: String): Flow<SseEvent> = callbackFlow {
        val url = RetrofitClient.getBaseUrl().trimEnd('/') + streamUrl

        val request = Request.Builder()
            .url(url)
            .header("Accept", "text/event-stream")
            .build()

        val listener = object : EventSourceListener() {
            override fun onEvent(
                eventSource: EventSource,
                id: String?,
                type: String?,
                data: String
            ) {
                val event = parseEvent(type, data)
                if (event != null) {
                    trySend(event)
                }
            }

            override fun onFailure(
                eventSource: EventSource,
                t: Throwable?,
                response: Response?
            ) {
                val errorMsg = t?.message ?: response?.message ?: "未知错误"
                trySend(SseEvent.Error(errorMsg))
                close(t)
            }

            override fun onClosed(eventSource: EventSource) {
                close()
            }
        }

        val factory = EventSources.createFactory(RetrofitClient.okHttpClient)
        eventSource = factory.newEventSource(request, listener)

        awaitClose {
            eventSource?.cancel()
            eventSource = null
        }
    }

    fun disconnect() {
        eventSource?.cancel()
        eventSource = null
    }

    private fun parseEvent(type: String?, data: String): SseEvent? {
        return when (type) {
            "candidates" -> {
                val json = gson.fromJson(data, JsonObject::class.java)
                val candidates = gson.fromJson(json.get("candidates"), Array<Candidate>::class.java)
                SseEvent.Candidates(candidates.toList())
            }
            "delta_text" -> {
                val json = gson.fromJson(data, JsonObject::class.java)
                val text = json.get("text")?.asString ?: ""
                SseEvent.DeltaText(text)
            }
            "citations" -> {
                val json = gson.fromJson(data, JsonObject::class.java)
                val citations = gson.fromJson(json.get("citations"), Array<Citation>::class.java)
                SseEvent.Citations(citations.toList())
            }
            "final" -> {
                val finalEvent = gson.fromJson(data, FinalEvent::class.java)
                SseEvent.Final(finalEvent)
            }
            else -> null
        }
    }
}
