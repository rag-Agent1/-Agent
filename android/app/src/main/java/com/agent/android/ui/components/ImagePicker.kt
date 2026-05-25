package com.agent.android.ui.components

import android.Manifest
import android.net.Uri
import android.os.Environment
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.width
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.CameraAlt
import androidx.compose.material.icons.filled.PhotoLibrary
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.core.content.FileProvider
import java.io.File

@Composable
fun rememberImagePickerState(): ImagePickerState {
    return remember { ImagePickerState() }
}

class ImagePickerState {
    var cameraUri by mutableStateOf<Uri?>(null)
}

@Composable
fun ImagePickerDialog(
    state: ImagePickerState,
    cameraPermissionLauncher: androidx.activity.result.ActivityResultLauncher<String>,
    galleryLauncher: androidx.activity.result.ActivityResultLauncher<String>,
    cameraUriProvider: () -> Uri?,
    onCameraUriReady: (Uri) -> Unit,
    onDismiss: () -> Unit
) {
    val context = LocalContext.current

    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("选择图片来源") },
        text = {
            Row {
                TextButton(
                    onClick = {
                        val uri = createTempImageUri(context)
                        onCameraUriReady(uri)
                        cameraPermissionLauncher.launch(Manifest.permission.CAMERA)
                        onDismiss()
                    }
                ) {
                    Icon(Icons.Default.CameraAlt, contentDescription = null)
                    Spacer(Modifier.width(8.dp))
                    Text("拍照")
                }
                TextButton(
                    onClick = {
                        galleryLauncher.launch("image/*")
                        onDismiss()
                    }
                ) {
                    Icon(Icons.Default.PhotoLibrary, contentDescription = null)
                    Spacer(Modifier.width(8.dp))
                    Text("相册")
                }
            }
        },
        confirmButton = {},
        dismissButton = {
            TextButton(onClick = onDismiss) {
                Text("取消")
            }
        }
    )
}

private fun createTempImageUri(context: android.content.Context): Uri {
    val tempFile = File(
        context.getExternalFilesDir(Environment.DIRECTORY_PICTURES),
        "camera_${System.currentTimeMillis()}.jpg"
    )
    return FileProvider.getUriForFile(
        context,
        "${context.packageName}.fileprovider",
        tempFile
    )
}
