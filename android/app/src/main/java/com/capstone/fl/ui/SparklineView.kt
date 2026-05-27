package com.capstone.fl.ui

import android.content.Context
import android.graphics.Canvas
import android.graphics.Paint
import android.graphics.Path
import android.util.AttributeSet
import android.view.View
import com.capstone.fl.R

/** Lightweight Canvas sparkline. No 3rd-party chart deps.
 *  Pass values in [0,1] (e.g. accuracy) via [setData]. */
class SparklineView @JvmOverloads constructor(
    ctx: Context, attrs: AttributeSet? = null
) : View(ctx, attrs) {

    private var values: FloatArray = floatArrayOf()
    private val linePaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        style = Paint.Style.STROKE
        strokeWidth = dp(2.2f)
        strokeCap = Paint.Cap.ROUND
        strokeJoin = Paint.Join.ROUND
        color = ctx.getColor(R.color.brand_violet)
    }
    private val fillPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        style = Paint.Style.FILL
        color = ctx.getColor(R.color.brand_violet_soft)
    }
    private val dotPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = ctx.getColor(R.color.brand_violet)
    }
    private val emptyPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = ctx.getColor(R.color.ink_muted)
        textSize = dp(11f)
    }
    private val path = Path()
    private val fillPath = Path()

    fun setData(v: FloatArray) {
        values = v
        invalidate()
    }

    override fun onDraw(canvas: Canvas) {
        val w = width.toFloat()
        val h = height.toFloat()
        val pad = dp(4f)
        if (values.size < 2) {
            canvas.drawText("학습 이력 없음", pad, h - pad, emptyPaint)
            return
        }
        val mn = values.min()
        val mx = values.max()
        val span = (mx - mn).coerceAtLeast(0.001f)

        val n = values.size
        val xs = FloatArray(n)
        val ys = FloatArray(n)
        for (i in 0 until n) {
            xs[i] = pad + (w - 2 * pad) * (i.toFloat() / (n - 1).toFloat())
            // Stretch the range a bit so a near-flat series still shows shape.
            val t = (values[i] - mn) / span
            ys[i] = (h - pad) - (h - 2 * pad) * t
        }

        path.reset(); fillPath.reset()
        path.moveTo(xs[0], ys[0]); fillPath.moveTo(xs[0], h - pad)
        fillPath.lineTo(xs[0], ys[0])
        for (i in 1 until n) {
            path.lineTo(xs[i], ys[i])
            fillPath.lineTo(xs[i], ys[i])
        }
        fillPath.lineTo(xs[n - 1], h - pad); fillPath.close()
        canvas.drawPath(fillPath, fillPaint)
        canvas.drawPath(path, linePaint)
        // last-point dot
        canvas.drawCircle(xs[n - 1], ys[n - 1], dp(3.5f), dotPaint)
    }

    private fun dp(v: Float) = v * resources.displayMetrics.density
}
