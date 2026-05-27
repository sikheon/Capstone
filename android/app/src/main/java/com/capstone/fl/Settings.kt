package com.capstone.fl

import android.content.Context
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey

/** Persists server URL, provisioned credentials, and a tiny local
 *  participation ledger so the UI can show "you've contributed N rounds"
 *  without round-tripping the server. */
class Settings(ctx: Context) {
    private val prefs = EncryptedSharedPreferences.create(
        ctx,
        "fl_settings",
        MasterKey.Builder(ctx).setKeyScheme(MasterKey.KeyScheme.AES256_GCM).build(),
        EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
        EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM,
    )

    var serverUrl: String
        get() = prefs.getString("server_url", BuildConfig.DEFAULT_SERVER_URL) ?: BuildConfig.DEFAULT_SERVER_URL
        set(v) { prefs.edit().putString("server_url", v).apply() }

    var clientId: String?
        get() = prefs.getString("client_id", null)
        set(v) { prefs.edit().putString("client_id", v).apply() }

    var clientSecret: String?
        get() = prefs.getString("client_secret", null)
        set(v) { prefs.edit().putString("client_secret", v).apply() }

    // ───── server-decided modules (kept for swap-on-the-fly) ─────
    var algorithm: String
        get() = prefs.getString("algorithm", "fedavg") ?: "fedavg"
        set(v) { prefs.edit().putString("algorithm", v).apply() }
    var model: String
        get() = prefs.getString("model", "cnn_mnist") ?: "cnn_mnist"
        set(v) { prefs.edit().putString("model", v).apply() }
    var dataset: String
        get() = prefs.getString("dataset", "mnist") ?: "mnist"
        set(v) { prefs.edit().putString("dataset", v).apply() }

    /** Background collector name — "none" means "use the registered static
     *  DatasetLoader for `dataset`". See data/DataCollector.kt. */
    var collector: String
        get() = prefs.getString("collector", "none") ?: "none"
        set(v) { prefs.edit().putString("collector", v).apply() }

    // ───── local participation ledger ─────
    var contributedRounds: Int
        get() = prefs.getInt("contributed_rounds", 0)
        set(v) { prefs.edit().putInt("contributed_rounds", v).apply() }

    var lastTrainAcc: Float
        get() = prefs.getFloat("last_train_acc", -1f)
        set(v) { prefs.edit().putFloat("last_train_acc", v).apply() }

    var lastTrainLoss: Float
        get() = prefs.getFloat("last_train_loss", -1f)
        set(v) { prefs.edit().putFloat("last_train_loss", v).apply() }

    var lastContributedAt: Long
        get() = prefs.getLong("last_contributed_at", 0L)
        set(v) { prefs.edit().putLong("last_contributed_at", v).apply() }

    /** Live progress label written by FLWorker so the UI can show "학습 중…" etc.
     *  Reset to empty when the worker finishes a cycle. */
    var stage: String
        get() = prefs.getString("stage", "") ?: ""
        set(v) { prefs.edit().putString("stage", v).apply() }

    var stageAt: Long
        get() = prefs.getLong("stage_at", 0L)
        set(v) { prefs.edit().putLong("stage_at", v).apply() }

    fun updateStage(s: String) {
        prefs.edit().putString("stage", s).putLong("stage_at", System.currentTimeMillis()).apply()
    }

    fun bumpContribution(acc: Float, loss: Float) {
        val hist = (accHistory + acc).takeLast(HISTORY_CAP)
        prefs.edit()
            .putInt("contributed_rounds", contributedRounds + 1)
            .putFloat("last_train_acc", acc)
            .putFloat("last_train_loss", loss)
            .putLong("last_contributed_at", System.currentTimeMillis())
            .putString("acc_history", hist.joinToString(","))
            .apply()
    }

    /** Recent local-train accuracies (oldest → newest), capped at HISTORY_CAP. */
    val accHistory: List<Float>
        get() = prefs.getString("acc_history", "")
            ?.takeIf { it.isNotBlank() }
            ?.split(",")
            ?.mapNotNull { it.toFloatOrNull() }
            ?: emptyList()

    fun clearCredentials() {
        prefs.edit().remove("client_id").remove("client_secret").apply()
    }

    companion object {
        private const val HISTORY_CAP = 20
    }
}
