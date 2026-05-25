package com.agent.android.data

import android.content.Context
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.map

private val Context.dataStore by preferencesDataStore(name = "agent_settings")

class SessionManager(private val context: Context) {

    companion object {
        private val KEY_SESSION_ID = stringPreferencesKey("session_id")
        private val KEY_BASE_URL = stringPreferencesKey("base_url")
    }

    val sessionId: Flow<String?> = context.dataStore.data.map { prefs ->
        prefs[KEY_SESSION_ID]
    }

    suspend fun saveSessionId(id: String) {
        context.dataStore.edit { prefs ->
            prefs[KEY_SESSION_ID] = id
        }
    }

    suspend fun clearSession() {
        context.dataStore.edit { prefs ->
            prefs.remove(KEY_SESSION_ID)
        }
    }

    suspend fun getSessionId(): String? {
        return context.dataStore.data.first()[KEY_SESSION_ID]
    }

    val baseUrl: Flow<String?> = context.dataStore.data.map { prefs ->
        prefs[KEY_BASE_URL]
    }

    suspend fun saveBaseUrl(url: String) {
        context.dataStore.edit { prefs ->
            prefs[KEY_BASE_URL] = url
        }
    }

    suspend fun getBaseUrl(): String? {
        return context.dataStore.data.first()[KEY_BASE_URL]
    }
}
