package com.agent.android.data

import android.content.Context
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.net.Uri
import java.io.ByteArrayOutputStream

object ImageCompressor {

    private const val MAX_DIMENSION = 1920
    private const val MAX_SIZE_BYTES = 4 * 1024 * 1024L // 4MB
    private const val QUALITY_STEP = 10
    private const val MIN_QUALITY = 20

    fun compress(context: Context, uri: Uri): ByteArray {
        val inputStream = context.contentResolver.openInputStream(uri)
            ?: throw IllegalStateException("无法读取图片")
        val bytes = inputStream.use { it.readBytes() }
        return compress(bytes)
    }

    fun compress(imageBytes: ByteArray): ByteArray {
        // 1. 解析尺寸但不加载全图
        val options = BitmapFactory.Options().apply {
            inJustDecodeBounds = true
        }
        BitmapFactory.decodeByteArray(imageBytes, 0, imageBytes.size, options)

        val (width, height) = options.outWidth to options.outHeight

        // 2. 计算采样率
        val sampleSize = computeSampleSize(width, height)
        val decodeOptions = BitmapFactory.Options().apply {
            inSampleSize = sampleSize
        }

        val bitmap = BitmapFactory.decodeByteArray(imageBytes, 0, imageBytes.size, decodeOptions)
            ?: throw IllegalStateException("图片解码失败")

        // 3. 如果仍超过最大尺寸，进行缩放
        val scaledBitmap = if (bitmap.width > MAX_DIMENSION || bitmap.height > MAX_DIMENSION) {
            val scale = minOf(
                MAX_DIMENSION.toFloat() / bitmap.width,
                MAX_DIMENSION.toFloat() / bitmap.height
            )
            Bitmap.createScaledBitmap(
                bitmap,
                (bitmap.width * scale).toInt(),
                (bitmap.height * scale).toInt(),
                true
            ).also { bitmap.recycle() }
        } else {
            bitmap
        }

        // 4. 质量压缩到 ≤ 4MB
        return compressToSize(scaledBitmap, MAX_SIZE_BYTES).also {
            scaledBitmap.recycle()
        }
    }

    private fun computeSampleSize(width: Int, height: Int): Int {
        var sampleSize = 1
        while (width / sampleSize > MAX_DIMENSION || height / sampleSize > MAX_DIMENSION) {
            sampleSize *= 2
        }
        return sampleSize
    }

    private fun compressToSize(bitmap: Bitmap, maxSize: Long): ByteArray {
        var quality = 90
        val output = ByteArrayOutputStream()

        while (quality >= MIN_QUALITY) {
            output.reset()
            bitmap.compress(Bitmap.CompressFormat.JPEG, quality, output)
            if (output.size() <= maxSize) break
            quality -= QUALITY_STEP
        }

        return output.toByteArray()
    }
}
