package com.capstone.fl.worker

import android.content.Context
import androidx.work.*
import java.util.concurrent.TimeUnit

/** WorkManager wiring. Two ways to participate in FL:
 *
 *  - `enablePeriodic(ctx)` — Gboard-style. PeriodicWorkRequest with strict
 *    Constraints (charging + unmetered network + idle + battery not low).
 *    Min interval is 15 minutes; WorkManager picks the actual time.
 *
 *  - `runOnce(ctx)` — one-shot, no constraints. Useful for "Run now" demo
 *    buttons and tests where you don't want to wait for the device to be
 *    plugged in and idle. */
object FLScheduler {

    private const val PERIODIC_TAG = "fl-periodic"

    fun enablePeriodic(ctx: Context) {
        val constraints = Constraints.Builder()
            .setRequiresCharging(true)
            .setRequiredNetworkType(NetworkType.UNMETERED)
            .setRequiresDeviceIdle(true)
            .setRequiresBatteryNotLow(true)
            .build()

        // NOTE: setBackoffCriteria() is incompatible with setRequiresDeviceIdle(true) on
        // Android 12+ (PeriodicWorkRequest$Builder throws IllegalArgumentException). The
        // default JobScheduler backoff is fine for an FL polling cycle.
        val req = PeriodicWorkRequestBuilder<FLWorker>(15, TimeUnit.MINUTES)
            .setConstraints(constraints)
            .addTag(PERIODIC_TAG)
            .build()

        WorkManager.getInstance(ctx).enqueueUniquePeriodicWork(
            PERIODIC_TAG,
            ExistingPeriodicWorkPolicy.UPDATE,
            req,
        )
    }

    fun disablePeriodic(ctx: Context) {
        WorkManager.getInstance(ctx).cancelUniqueWork(PERIODIC_TAG)
    }

    fun isPeriodicEnabled(ctx: Context): Boolean {
        val list = WorkManager.getInstance(ctx).getWorkInfosForUniqueWork(PERIODIC_TAG).get()
        return list.any { !it.state.isFinished }
    }

    fun runOnce(ctx: Context) {
        val req = OneTimeWorkRequestBuilder<FLWorker>()
            .setConstraints(Constraints.Builder()
                .setRequiredNetworkType(NetworkType.CONNECTED)
                .build())
            .build()
        WorkManager.getInstance(ctx).enqueue(req)
    }
}
