package com.capstone.fl.reporter

import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.net.ConnectivityManager
import android.net.NetworkCapabilities
import android.os.BatteryManager
import org.json.JSONObject

/** Ultra-light state probe (the "초경량 플래그 추출기"). Reads only what the
 * server-side dropout predictor needs. */
class LocalReporter(private val ctx: Context) {

    fun snapshot(clientId: String, kind: String = "android"): JSONObject {
        val battery = readBattery()
        val net = readNetwork()
        return JSONObject()
            .put("client_id", clientId)
            .put("kind", kind)
            .put("battery", battery.first)
            .put("charging", battery.second)
            .put("network", net)
            .put("cpu_load", JSONObject.NULL)
    }

    private fun readBattery(): Pair<Double?, Boolean?> {
        val bm = ctx.getSystemService(Context.BATTERY_SERVICE) as BatteryManager?
            ?: return null to null
        val pct = bm.getIntProperty(BatteryManager.BATTERY_PROPERTY_CAPACITY)
        val batteryStatus: Intent? = ctx.registerReceiver(null, IntentFilter(Intent.ACTION_BATTERY_CHANGED))
        val status = batteryStatus?.getIntExtra(BatteryManager.EXTRA_STATUS, -1) ?: -1
        val charging = status == BatteryManager.BATTERY_STATUS_CHARGING ||
                       status == BatteryManager.BATTERY_STATUS_FULL
        return (pct / 100.0) to charging
    }

    private fun readNetwork(): String {
        val cm = ctx.getSystemService(Context.CONNECTIVITY_SERVICE) as ConnectivityManager
        val net = cm.activeNetwork ?: return "none"
        val caps = cm.getNetworkCapabilities(net) ?: return "none"
        return when {
            caps.hasTransport(NetworkCapabilities.TRANSPORT_WIFI)     -> "wifi"
            caps.hasTransport(NetworkCapabilities.TRANSPORT_CELLULAR) -> "cell"
            caps.hasTransport(NetworkCapabilities.TRANSPORT_ETHERNET) -> "ethernet"
            else -> "none"
        }
    }
}
