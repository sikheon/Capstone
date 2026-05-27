package com.capstone.fl.service

import android.app.*
import android.content.Context
import android.content.Intent
import android.os.Build
import android.os.IBinder
import android.os.Process
import com.capstone.fl.Settings
import com.capstone.fl.network.FLApi
import com.capstone.fl.reporter.LocalReporter
import org.json.JSONObject
import java.util.concurrent.atomic.AtomicBoolean

class FLService : Service() {
    companion object {
        const val CHANNEL_ID = "fl_service"
        const val NOTIFICATION_ID = 1001
        fun start(ctx: Context) = ctx.startForegroundService(Intent(ctx, FLService::class.java))
        fun stop(ctx: Context)  = ctx.stopService(Intent(ctx, FLService::class.java))
    }

    private val running = AtomicBoolean(false)
    private lateinit var settings: Settings
    private lateinit var api: FLApi
    private lateinit var reporter: LocalReporter

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onCreate() {
        super.onCreate()
        settings = Settings(this)
        reporter = LocalReporter(this)
        api = FLApi(settings.serverUrl, settings.clientId, settings.clientSecret)
        startForeground(NOTIFICATION_ID, buildNotification("Connecting…"))
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        if (running.compareAndSet(false, true)) {
            Thread { loop() }.start()
        }
        return START_STICKY
    }

    override fun onDestroy() {
        running.set(false)
        super.onDestroy()
    }

    private fun loop() {
        Process.setThreadPriority(Process.THREAD_PRIORITY_BACKGROUND)
        ensureCredentials()
        registerOnce()
        while (running.get()) {
            try {
                val snap = reporter.snapshot(api.clientId ?: "android")
                val resp = api.heartbeat(snap)
                val state = resp.optString("orchestrator_state", "?")
                val mode  = resp.optString("mode", "?")
                val round = if (resp.isNull("round")) "-" else resp.optInt("round").toString()
                val mine  = resp.optBoolean("selected_for_round", false)
                val line  = "FL: $state ($mode) • round $round" + if (mine) " • selected" else ""
                updateNotification(line)
            } catch (e: Exception) {
                updateNotification("err: ${e.message}")
            }
            Thread.sleep(5000)
        }
    }

    private fun ensureCredentials() {
        if (api.clientId != null && api.clientSecret != null) return
        val (id, sec) = api.provision(suggested = null)
        settings.clientId = id; settings.clientSecret = sec
    }

    private fun registerOnce() {
        val info = JSONObject()
            .put("client_id", api.clientId)
            .put("kind", "android")
            .put("os", "Android")
            .put("arch", Build.SUPPORTED_ABIS.firstOrNull() ?: "unknown")
            .put("hostname", Build.MODEL)
            .put("model_hw", "${Build.MANUFACTURER} ${Build.MODEL}")
            .put("app_version", "0.1.0")
            .put("metadata", JSONObject().put("sdk", Build.VERSION.SDK_INT))
        try { api.register(info) } catch (_: Exception) {}
    }

    private fun buildNotification(text: String): Notification {
        val nm = getSystemService(NotificationManager::class.java)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O &&
            nm.getNotificationChannel(CHANNEL_ID) == null) {
            nm.createNotificationChannel(
                NotificationChannel(CHANNEL_ID, "FL participation", NotificationManager.IMPORTANCE_LOW)
            )
        }
        return Notification.Builder(this, CHANNEL_ID)
            .setSmallIcon(android.R.drawable.stat_sys_upload)
            .setContentTitle("FL Client")
            .setContentText(text)
            .setOngoing(true)
            .build()
    }

    private fun updateNotification(text: String) {
        getSystemService(NotificationManager::class.java)
            .notify(NOTIFICATION_ID, buildNotification(text))
    }
}
