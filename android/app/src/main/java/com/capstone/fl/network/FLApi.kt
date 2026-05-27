package com.capstone.fl.network

import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONObject
import java.util.concurrent.TimeUnit

/** Lightweight client to the FL server. All requests target [baseUrl], so the
 * user can point the app at any coordinator without rebuilding. */
class FLApi(
    @Volatile var baseUrl: String,
    @Volatile var clientId: String? = null,
    @Volatile var clientSecret: String? = null,
) {
    private val http = OkHttpClient.Builder()
        .callTimeout(15, TimeUnit.SECONDS)
        .build()

    private val JSON = "application/json".toMediaType()

    private fun urlOf(path: String) = baseUrl.trimEnd('/') + path

    private fun postJson(path: String, body: JSONObject, needsAuth: Boolean = false): JSONObject {
        val rb = Request.Builder()
            .url(urlOf(path))
            .post(body.toString().toRequestBody(JSON))
            // localtunnel shows an HTML interstitial on first hit unless we
            // identify ourselves with this header — skip it.
            .addHeader("bypass-tunnel-reminder", "1")
            .addHeader("User-Agent", "fl-android/0.3")
        if (needsAuth) {
            rb.addHeader("X-Client-Id", clientId ?: "")
            rb.addHeader("X-Client-Secret", clientSecret ?: "")
        }
        http.newCall(rb.build()).execute().use { resp ->
            val text = resp.body?.string().orEmpty()
            if (!resp.isSuccessful) error("${resp.code} ${resp.message} - $text")
            return if (text.isBlank()) JSONObject() else JSONObject(text)
        }
    }

    private fun getJson(path: String, needsAuth: Boolean = false): JSONObject {
        val rb = Request.Builder().url(urlOf(path)).get()
            .addHeader("bypass-tunnel-reminder", "1")
            .addHeader("User-Agent", "fl-android/0.3")
        if (needsAuth) {
            rb.addHeader("X-Client-Id", clientId ?: "")
            rb.addHeader("X-Client-Secret", clientSecret ?: "")
        }
        http.newCall(rb.build()).execute().use { resp ->
            val text = resp.body?.string().orEmpty()
            if (!resp.isSuccessful) error("${resp.code} ${resp.message} - $text")
            return if (text.isBlank()) JSONObject() else JSONObject(text)
        }
    }

    fun provision(suggested: String? = null): Pair<String, String> {
        val body = JSONObject()
        if (suggested != null) body.put("suggested_id", suggested)
        val r = postJson("/api/provision", body)
        val id = r.getString("client_id")
        val sec = r.getString("client_secret")
        clientId = id; clientSecret = sec
        return id to sec
    }

    fun register(info: JSONObject) = postJson("/api/register", info, needsAuth = true)
    fun heartbeat(info: JSONObject) = postJson("/api/heartbeat", info, needsAuth = true)
    fun submitUpdate(payload: JSONObject) = postJson("/api/update", payload, needsAuth = true)
    fun currentRound() = getJson("/api/round/current", needsAuth = true)
    fun datasetSample(name: String, n: Int) = getJson("/api/dataset/$name/sample?n=$n", needsAuth = true)

    fun status() = getJson("/api/status")
    fun registry() = getJson("/api/registry")

    /** GET /api/clients returns a top-level array; expose it as a list of JSONObjects. */
    fun clients(): List<JSONObject> {
        val rb = Request.Builder().url(urlOf("/api/clients")).get()
            .addHeader("bypass-tunnel-reminder", "1")
            .addHeader("User-Agent", "fl-android/0.3")
        http.newCall(rb.build()).execute().use { resp ->
            val text = resp.body?.string().orEmpty()
            if (!resp.isSuccessful || text.isBlank()) return emptyList()
            val arr = org.json.JSONArray(text)
            return List(arr.length()) { arr.getJSONObject(it) }
        }
    }

    /** GET /api/metrics returns an array; we wrap it as {"items": [...]} so the
     *  caller can read latest accuracy without writing extra plumbing. */
    fun latestMetric(): JSONObject? {
        val rb = Request.Builder().url(urlOf("/api/metrics")).get()
            .addHeader("bypass-tunnel-reminder", "1")
            .addHeader("User-Agent", "fl-android/0.3")
        http.newCall(rb.build()).execute().use { resp ->
            val text = resp.body?.string().orEmpty()
            if (!resp.isSuccessful || text.isBlank()) return null
            val arr = org.json.JSONArray(text)
            if (arr.length() == 0) return null
            return arr.getJSONObject(arr.length() - 1)
        }
    }

    /** GET /api/global_model — server-side eval of the current global model. */
    fun globalEval(): JSONObject? {
        val rb = Request.Builder().url(urlOf("/api/global_model")).get()
            .addHeader("bypass-tunnel-reminder", "1")
            .addHeader("User-Agent", "fl-android/0.3")
        http.newCall(rb.build()).execute().use { resp ->
            val text = resp.body?.string().orEmpty()
            if (!resp.isSuccessful || text.isBlank()) return null
            return JSONObject(text)
        }
    }
}

