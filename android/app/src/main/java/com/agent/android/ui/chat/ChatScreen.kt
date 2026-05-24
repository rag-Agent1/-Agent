package com.agent.android.ui.chat

import android.net.Uri
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.CameraAlt
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.ExpandLess
import androidx.compose.material.icons.filled.ExpandMore
import androidx.compose.material.icons.filled.Info
import androidx.compose.material.icons.filled.Send
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material.icons.filled.Stop
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.material3.rememberModalBottomSheetState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.viewmodel.compose.viewModel
import coil.compose.AsyncImage
import com.agent.android.data.model.Candidate
import com.agent.android.data.model.ChatMessage
import com.agent.android.data.model.Citation
import com.agent.android.data.model.ConnectionStatus
import com.agent.android.data.model.MessageRole
import com.agent.android.data.SessionManager
import com.agent.android.ui.components.ImagePickerDialog
import com.agent.android.ui.components.rememberImagePickerState
import com.agent.android.ui.theme.AgentTheme
import com.agent.android.ui.theme.ScoreHigh
import com.agent.android.ui.theme.ScoreLow
import com.agent.android.ui.theme.ScoreMedium
import com.agent.android.ui.theme.StatusGreen
import com.agent.android.ui.theme.StatusRed
import com.agent.android.viewmodel.ChatViewModel

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ChatScreen(
    onOpenSettings: () -> Unit = {},
    viewModel: ChatViewModel = viewModel(
        factory = ChatViewModel.Factory(
            sessionManager = SessionManager(LocalContext.current)
        )
    )
) {
    val state by viewModel.uiState.collectAsState()
    val context = LocalContext.current
    val listState = rememberLazyListState()
    val imagePickerState = rememberImagePickerState()
    var textInput by remember { mutableStateOf("") }
    var showImagePicker by remember { mutableStateOf(false) }

    // 相册选取
    val galleryLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.GetContent()
    ) { uri: Uri? ->
        uri?.let { viewModel.onImageSelected(it) }
    }

    // 相机拍照（用 try-catch 防止崩溃）
    val cameraLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.TakePicture()
    ) { success ->
        if (success && imagePickerState.cameraUri != null) {
            viewModel.onImageSelected(imagePickerState.cameraUri!!)
        }
    }

    // 相机权限
    val cameraPermissionLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.RequestPermission()
    ) { granted ->
        if (granted && imagePickerState.cameraUri != null) {
            try {
                cameraLauncher.launch(imagePickerState.cameraUri!!)
            } catch (e: Exception) {
                viewModel.clearSelectedImage()
            }
        }
    }

    // 列表滚动到底部
    LaunchedEffect(state.messages.size, state.isStreaming) {
        if (state.messages.isNotEmpty()) {
            listState.animateScrollToItem(state.messages.size - 1)
        }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("AI导购") },
                actions = {
                    ConnectionIndicator(state.connectionStatus)
                    IconButton(onClick = { viewModel.newSession() }) {
                        Icon(Icons.Default.Add, contentDescription = "新会话")
                    }
                    IconButton(onClick = onOpenSettings) {
                        Icon(Icons.Default.Settings, contentDescription = "设置")
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = MaterialTheme.colorScheme.surface
                )
            )
        },
        bottomBar = {
            ChatBottomBar(
                text = textInput,
                onTextChange = { textInput = it },
                selectedImageUri = state.selectedImageUri,
                isStreaming = state.isStreaming,
                isUploading = state.isUploading,
                onSend = {
                    if (textInput.isNotBlank() || state.selectedImageUri != null) {
                        viewModel.sendMessage(context, textInput.ifBlank { null })
                        textInput = ""
                    }
                },
                onStop = { viewModel.stopGeneration() },
                onPickImage = { showImagePicker = true },
                onClearImage = { viewModel.clearSelectedImage() }
            )
        }
    ) { padding ->
        Box(modifier = Modifier.fillMaxSize().padding(padding)) {
            if (state.messages.isEmpty()) {
                EmptyState()
            } else {
                LazyColumn(
                    state = listState,
                    modifier = Modifier.fillMaxSize(),
                    contentPadding = PaddingValues(horizontal = 16.dp, vertical = 8.dp),
                    verticalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    items(state.messages, key = { it.id }) { message ->
                        MessageBubble(
                            message = message,
                            onClarifySend = { viewModel.sendClarification(it) }
                        )
                    }
                }
            }

            // 错误提示（含重试按钮）
            state.error?.let { error ->
                ErrorSnackbar(
                    message = error,
                    onDismiss = { viewModel.clearError() },
                    onRetry = { viewModel.retryLastMessage(context) },
                    modifier = Modifier.align(Alignment.BottomCenter)
                )
            }
        }
    }

    // 图片选择对话框
    if (showImagePicker) {
        ImagePickerDialog(
            state = imagePickerState,
            cameraPermissionLauncher = cameraPermissionLauncher,
            galleryLauncher = galleryLauncher,
            cameraUriProvider = { imagePickerState.cameraUri },
            onCameraUriReady = { uri -> imagePickerState.cameraUri = uri },
            onDismiss = { showImagePicker = false }
        )
    }
}

@Composable
private fun ConnectionIndicator(status: ConnectionStatus) {
    val color = when (status) {
        ConnectionStatus.CONNECTED -> StatusGreen
        ConnectionStatus.DISCONNECTED -> StatusRed
        ConnectionStatus.CHECKING -> Color.Gray
    }
    Box(
        modifier = Modifier
            .size(8.dp)
            .clip(CircleShape)
            .background(color)
            .padding(4.dp)
    )
}

@Composable
private fun EmptyState() {
    Box(
        modifier = Modifier.fillMaxSize(),
        contentAlignment = Alignment.Center
    ) {
        Column(horizontalAlignment = Alignment.CenterHorizontally) {
            Icon(
                Icons.Default.Info,
                contentDescription = null,
                modifier = Modifier.size(64.dp),
                tint = MaterialTheme.colorScheme.outline
            )
            Spacer(Modifier.height(16.dp))
            Text(
                "拍照或选择图片开始购物",
                style = MaterialTheme.typography.bodyLarge,
                color = MaterialTheme.colorScheme.outline
            )
            Spacer(Modifier.height(8.dp))
            Text(
                "拍下商品，AI 帮您找同款和替代品",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.outline
            )
        }
    }
}

@Composable
private fun ChatBottomBar(
    text: String,
    onTextChange: (String) -> Unit,
    selectedImageUri: Uri?,
    isStreaming: Boolean,
    isUploading: Boolean,
    onSend: () -> Unit,
    onStop: () -> Unit,
    onPickImage: () -> Unit,
    onClearImage: () -> Unit
) {
    Surface(
        shadowElevation = 8.dp,
        color = MaterialTheme.colorScheme.surface
    ) {
        Column(modifier = Modifier.padding(horizontal = 16.dp, vertical = 8.dp)) {
            // 图片预览
            selectedImageUri?.let { uri ->
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    AsyncImage(
                        model = uri,
                        contentDescription = "已选图片",
                        modifier = Modifier
                            .size(48.dp)
                            .clip(RoundedCornerShape(8.dp)),
                        contentScale = ContentScale.Crop
                    )
                    IconButton(onClick = onClearImage) {
                        Icon(Icons.Default.Close, contentDescription = "清除图片")
                    }
                }
            }

            // 上传进度
            if (isUploading) {
                LinearProgressIndicator(modifier = Modifier.fillMaxWidth())
                Spacer(Modifier.height(4.dp))
            }

            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically
            ) {
                // 图片选择按钮
                IconButton(onClick = onPickImage) {
                    Icon(Icons.Default.CameraAlt, contentDescription = "拍照/选图")
                }

                // 文字输入
                OutlinedTextField(
                    value = text,
                    onValueChange = onTextChange,
                    modifier = Modifier.weight(1f),
                    placeholder = { Text("输入问题或直接发送图片") },
                    singleLine = true,
                    shape = RoundedCornerShape(24.dp),
                    colors = OutlinedTextFieldDefaults.colors(
                        focusedBorderColor = MaterialTheme.colorScheme.primary,
                        unfocusedBorderColor = MaterialTheme.colorScheme.outline
                    )
                )

                Spacer(Modifier.width(8.dp))

                // 发送/停止按钮
                if (isStreaming) {
                    IconButton(onClick = onStop) {
                        Icon(
                            Icons.Default.Stop,
                            contentDescription = "停止生成",
                            tint = MaterialTheme.colorScheme.error
                        )
                    }
                } else {
                    IconButton(
                        onClick = onSend,
                        enabled = text.isNotBlank() || selectedImageUri != null
                    ) {
                        Icon(
                            Icons.Default.Send,
                            contentDescription = "发送",
                            tint = if (text.isNotBlank() || selectedImageUri != null)
                                MaterialTheme.colorScheme.primary
                            else
                                MaterialTheme.colorScheme.outline
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun MessageBubble(
    message: ChatMessage,
    onClarifySend: (String) -> Unit
) {
    val isUser = message.role == MessageRole.USER
    val alignment = if (isUser) Alignment.End else Alignment.Start
    val bgColor = if (isUser)
        MaterialTheme.colorScheme.primary
    else
        MaterialTheme.colorScheme.surfaceVariant
    val textColor = if (isUser)
        MaterialTheme.colorScheme.onPrimary
    else
        MaterialTheme.colorScheme.onSurfaceVariant

    Column(
        modifier = Modifier.fillMaxWidth(),
        horizontalAlignment = alignment
    ) {
        // 用户图片
        if (message.imageLocalUri != null && isUser) {
            AsyncImage(
                model = message.imageLocalUri,
                contentDescription = "用户图片",
                modifier = Modifier
                    .size(120.dp)
                    .clip(RoundedCornerShape(12.dp)),
                contentScale = ContentScale.Crop
            )
            Spacer(Modifier.height(4.dp))
        }

        // 气泡（用户仅传图时没有输入文字，不显示气泡）
        val hasContent = message.text.isNotBlank() ||
                !message.candidates.isNullOrEmpty() ||
                !message.citations.isNullOrEmpty() ||
                message.isLoading || message.isError
        if (hasContent) {
            Surface(
                shape = RoundedCornerShape(
                    topStart = 16.dp,
                    topEnd = 16.dp,
                    bottomStart = if (isUser) 16.dp else 4.dp,
                    bottomEnd = if (isUser) 4.dp else 16.dp
                ),
                color = bgColor,
                modifier = Modifier.widthIn(max = 320.dp)
            ) {
                Column(modifier = Modifier.padding(12.dp)) {
                    // 候选商品卡片
                    if (!message.candidates.isNullOrEmpty()) {
                        CandidateCardRow(message.candidates)
                        Spacer(Modifier.height(8.dp))
                    }

                    // 加载中：骨架屏
                    if (message.isLoading && !message.isStreaming) {
                        Text("正在搜索...", style = MaterialTheme.typography.bodySmall, modifier = Modifier.padding(bottom = 8.dp))
                        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                            repeat(3) { SkeletonCard() }
                        }
                    }

                    // 流式/完成文本
                    if (message.text.isNotBlank()) {
                        Text(
                            text = message.text,
                            color = if (isUser) textColor else MaterialTheme.colorScheme.onSurface,
                            style = MaterialTheme.typography.bodyMedium
                        )
                    }

                    // 引用
                    if (!message.citations.isNullOrEmpty()) {
                        Spacer(Modifier.height(8.dp))
                        CitationSection(message.citations)
                    }

                    // 错误
                    if (message.isError) {
                        Text(
                            text = message.errorMessage ?: "出错了",
                            color = MaterialTheme.colorScheme.error,
                            style = MaterialTheme.typography.bodySmall
                        )
                    }
                }
            }
        }

        // 澄清交互
        if (message.needClarify && message.clarifyQuestion != null) {
            Spacer(Modifier.height(8.dp))
            ClarifySection(
                question = message.clarifyQuestion,
                onSend = onClarifySend
            )
        }
    }
}

@Composable
private fun CandidateCardRow(candidates: List<Candidate>) {
    Column {
        Text(
            "候选商品",
            style = MaterialTheme.typography.labelLarge,
            color = MaterialTheme.colorScheme.primary,
            modifier = Modifier.padding(bottom = 4.dp)
        )
        LazyRow(
            horizontalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            items(candidates) { candidate ->
                CandidateCard(candidate)
            }
        }
    }
}

@Composable
private fun CandidateCard(candidate: Candidate) {
    var showDetail by remember { mutableStateOf(false) }

    Card(
        modifier = Modifier
            .width(140.dp)
            .clickable { showDetail = true },
        shape = RoundedCornerShape(12.dp),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
    ) {
        Column {
            // 商品图片
            Box {
                AsyncImage(
                    model = candidate.imageUrl,
                    contentDescription = candidate.title,
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(120.dp)
                        .clip(RoundedCornerShape(topStart = 12.dp, topEnd = 12.dp)),
                    contentScale = ContentScale.Crop
                )
                // 分数标签
                Surface(
                    color = scoreColor(candidate.score).copy(alpha = 0.85f),
                    shape = RoundedCornerShape(bottomStart = 8.dp),
                    modifier = Modifier.align(Alignment.TopEnd)
                ) {
                    Text(
                        "${(candidate.score * 100).toInt()}%",
                        modifier = Modifier.padding(horizontal = 6.dp, vertical = 2.dp),
                        color = Color.White,
                        fontSize = 11.sp,
                        fontWeight = FontWeight.Bold
                    )
                }
            }

            Column(modifier = Modifier.padding(8.dp)) {
                Text(
                    candidate.title,
                    style = MaterialTheme.typography.bodySmall,
                    maxLines = 2,
                    overflow = TextOverflow.Ellipsis
                )
                if (candidate.price != null) {
                    Text(
                        "¥${candidate.price}",
                        style = MaterialTheme.typography.labelLarge,
                        color = MaterialTheme.colorScheme.primary,
                        fontWeight = FontWeight.Bold
                    )
                }
            }
        }
    }

    // 商品详情 BottomSheet
    if (showDetail) {
        CandidateDetailSheet(
            candidate = candidate,
            onDismiss = { showDetail = false }
        )
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun CandidateDetailSheet(
    candidate: Candidate,
    onDismiss: () -> Unit
) {
    val sheetState = rememberModalBottomSheetState()
    ModalBottomSheet(
        onDismissRequest = onDismiss,
        sheetState = sheetState
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            AsyncImage(
                model = candidate.imageUrl,
                contentDescription = candidate.title,
                modifier = Modifier
                    .fillMaxWidth()
                    .height(240.dp)
                    .clip(RoundedCornerShape(12.dp)),
                contentScale = ContentScale.Crop
            )
            Spacer(Modifier.height(12.dp))
            Text(candidate.title, style = MaterialTheme.typography.titleMedium)
            if (candidate.price != null) {
                Text(
                    "¥${candidate.price}",
                    style = MaterialTheme.typography.headlineMedium,
                    color = MaterialTheme.colorScheme.primary,
                    fontWeight = FontWeight.Bold
                )
            }
            Spacer(Modifier.height(8.dp))
            Text(
                "相似度: ${(candidate.score * 100).toInt()}%",
                style = MaterialTheme.typography.bodyMedium
            )
            candidate.attrs?.let { attrs ->
                Spacer(Modifier.height(12.dp))
                Text("关键属性", style = MaterialTheme.typography.titleSmall)
                Spacer(Modifier.height(4.dp))
                attrs.forEach { (key, value) ->
                    Row {
                        Text("$key: ", style = MaterialTheme.typography.bodyMedium, fontWeight = FontWeight.Medium)
                        Text(value, style = MaterialTheme.typography.bodyMedium)
                    }
                }
            }
            Spacer(Modifier.height(24.dp))
        }
    }
}

@Composable
private fun CitationSection(citations: List<Citation>) {
    var expanded by remember { mutableStateOf(false) }

    Column {
        TextButton(
            onClick = { expanded = !expanded },
            contentPadding = PaddingValues(0.dp)
        ) {
            Text(
                "查看引用来源 (${citations.size})",
                style = MaterialTheme.typography.labelSmall,
                color = MaterialTheme.colorScheme.primary
            )
            Icon(
                if (expanded) Icons.Default.ExpandLess else Icons.Default.ExpandMore,
                contentDescription = null,
                modifier = Modifier.size(16.dp),
                tint = MaterialTheme.colorScheme.primary
            )
        }

        AnimatedVisibility(
            visible = expanded,
            enter = fadeIn(),
            exit = fadeOut()
        ) {
            Column {
                citations.forEachIndexed { index, citation ->
                    CitationItem(index + 1, citation)
                    if (index < citations.size - 1) {
                        HorizontalDivider(modifier = Modifier.padding(vertical = 4.dp))
                    }
                }
            }
        }
    }
}

@Composable
private fun CitationItem(index: Int, citation: Citation) {
    Column(modifier = Modifier.padding(start = 8.dp)) {
        Text(
            "[$index] ${citation.source}",
            style = MaterialTheme.typography.labelSmall,
            color = MaterialTheme.colorScheme.primary,
            fontWeight = FontWeight.Medium
        )
        Spacer(Modifier.height(2.dp))
        Text(
            "\"${citation.snippet}\"",
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
    }
}

@Composable
private fun ClarifySection(
    question: String,
    onSend: (String) -> Unit
) {
    var input by remember { mutableStateOf("") }

    Surface(
        shape = RoundedCornerShape(12.dp),
        color = MaterialTheme.colorScheme.tertiaryContainer
    ) {
        Column(modifier = Modifier.padding(12.dp)) {
            Text(
                question,
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onTertiaryContainer
            )
            Spacer(Modifier.height(8.dp))
            Row(verticalAlignment = Alignment.CenterVertically) {
                OutlinedTextField(
                    value = input,
                    onValueChange = { input = it },
                    modifier = Modifier.weight(1f),
                    placeholder = { Text("请输入...") },
                    singleLine = true,
                    shape = RoundedCornerShape(20.dp)
                )
                Spacer(Modifier.width(8.dp))
                Button(
                    onClick = {
                        onSend(input)
                        input = ""
                    },
                    enabled = input.isNotBlank(),
                    shape = CircleShape
                ) {
                    Text("发送")
                }
            }
        }
    }
}

@Composable
private fun ErrorSnackbar(
    message: String,
    onDismiss: () -> Unit,
    onRetry: (() -> Unit)? = null,
    modifier: Modifier = Modifier
) {
    Surface(
        modifier = modifier.padding(16.dp),
        shape = RoundedCornerShape(12.dp),
        color = MaterialTheme.colorScheme.errorContainer,
        shadowElevation = 4.dp
    ) {
        Row(
            modifier = Modifier.padding(12.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text(
                message,
                modifier = Modifier.weight(1f),
                color = MaterialTheme.colorScheme.onErrorContainer,
                style = MaterialTheme.typography.bodySmall
            )
            if (onRetry != null) {
                TextButton(onClick = onRetry) {
                    Text("重试", color = MaterialTheme.colorScheme.onErrorContainer)
                }
            }
            TextButton(onClick = onDismiss) {
                Text("关闭", color = MaterialTheme.colorScheme.onErrorContainer)
            }
        }
    }
}

@Composable
private fun SkeletonCard() {
    Card(
        modifier = Modifier.width(140.dp),
        shape = RoundedCornerShape(12.dp),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
    ) {
        Column {
            // 图片占位
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .height(120.dp)
                    .background(MaterialTheme.colorScheme.surfaceVariant)
            )
            // 文字占位
            Column(modifier = Modifier.padding(8.dp)) {
                Box(
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(12.dp)
                        .clip(RoundedCornerShape(4.dp))
                        .background(MaterialTheme.colorScheme.surfaceVariant)
                )
                Spacer(Modifier.height(6.dp))
                Box(
                    modifier = Modifier
                        .width(60.dp)
                        .height(12.dp)
                        .clip(RoundedCornerShape(4.dp))
                        .background(MaterialTheme.colorScheme.surfaceVariant)
                )
            }
        }
    }
}

private fun scoreColor(score: Double): Color {
    return when {
        score >= 0.8 -> ScoreHigh
        score >= 0.6 -> ScoreMedium
        else -> ScoreLow
    }
}

// ==================== @Preview 预览（Android Studio 中可见） ====================

private val mockCandidates = listOf(
    Candidate("SKU001", 0.92, "索尼 WH-1000XM5 无线降噪耳机", "https://picsum.photos/200?random=1", mapOf("品牌" to "索尼", "颜色" to "黑色"), 2999.0),
    Candidate("SKU002", 0.87, "Bose QC45 无线降噪耳机", "https://picsum.photos/200?random=2", mapOf("品牌" to "Bose", "颜色" to "银色"), 2499.0),
)

private val mockCitations = listOf(
    Citation("SKU001", "c01", "采用新一代HD降噪处理器QN1", "索尼官方详情页"),
    Citation("SKU001", "c02", "续航最长40小时，支持快充", "索尼官方详情页"),
)

@Preview(showBackground = true, showSystemUi = true)
@Composable
private fun ChatScreenEmptyPreview() {
    AgentTheme {
        Box(modifier = Modifier.fillMaxSize()) {
            EmptyState()
        }
    }
}

@Preview(showBackground = true, showSystemUi = false)
@Composable
private fun ChatBottomBarPreview() {
    AgentTheme {
        ChatBottomBar(
            text = "",
            onTextChange = {},
            selectedImageUri = null,
            isStreaming = false,
            isUploading = false,
            onSend = {},
            onStop = {},
            onPickImage = {},
            onClearImage = {}
        )
    }
}

@Preview(showBackground = true, showSystemUi = false)
@Composable
private fun ChatBottomBarWithTextPreview() {
    AgentTheme {
        ChatBottomBar(
            text = "推荐类似的商品",
            onTextChange = {},
            selectedImageUri = null,
            isStreaming = false,
            isUploading = false,
            onSend = {},
            onStop = {},
            onPickImage = {},
            onClearImage = {}
        )
    }
}

@Preview(showBackground = true, showSystemUi = false)
@Composable
private fun CandidateCardPreview() {
    AgentTheme {
        CandidateCard(mockCandidates[0])
    }
}

@Preview(showBackground = true, showSystemUi = false)
@Composable
private fun CandidateCardRowPreview() {
    AgentTheme {
        CandidateCardRow(mockCandidates)
    }
}

@Preview(showBackground = true, showSystemUi = false)
@Composable
private fun CitationSectionPreview() {
    AgentTheme {
        CitationSection(mockCitations)
    }
}

@Preview(showBackground = true, showSystemUi = false)
@Composable
private fun ClarifySectionPreview() {
    AgentTheme {
        ClarifySection(question = "您更看重降噪效果还是舒适度？", onSend = {})
    }
}

@Preview(showBackground = true, showSystemUi = false)
@Composable
private fun ErrorSnackbarPreview() {
    AgentTheme {
        ErrorSnackbar(message = "网络连接失败，请检查后端服务", onDismiss = {}, onRetry = {}, modifier = Modifier.padding(16.dp))
    }
}

@Preview(showBackground = true, showSystemUi = false)
@Composable
private fun SkeletonCardPreview() {
    AgentTheme {
        SkeletonCard()
    }
}

@Preview(showBackground = true, showSystemUi = false)
@Composable
private fun MessageBubbleUserPreview() {
    AgentTheme {
        MessageBubble(
            message = ChatMessage(
                id = "preview_user",
                role = MessageRole.USER,
                text = "推荐类似这款的商品",
                imageLocalUri = null,
            ),
            onClarifySend = {}
        )
    }
}

@Preview(showBackground = true, showSystemUi = false, heightDp = 400)
@Composable
private fun MessageBubbleAssistantPreview() {
    AgentTheme {
        MessageBubble(
            message = ChatMessage(
                id = "preview_asst",
                role = MessageRole.ASSISTANT,
                text = "根据您拍摄的图片，我推荐这款索尼 WH-1000XM5 耳机，它的黑色外观和您的图片高度匹配，降噪效果出色。",
                candidates = mockCandidates,
                citations = mockCitations,
                isLoading = false,
                isStreaming = false,
            ),
            onClarifySend = {}
        )
    }
}

@Preview(showBackground = true, showSystemUi = false, heightDp = 300)
@Composable
private fun MessageBubbleClarifyPreview() {
    AgentTheme {
        MessageBubble(
            message = ChatMessage(
                id = "preview_clarify",
                role = MessageRole.ASSISTANT,
                text = "根据图片未能精确匹配到商品。",
                needClarify = true,
                clarifyQuestion = "您更看重降噪效果还是舒适度？",
            ),
            onClarifySend = {}
        )
    }
}

@Preview(showBackground = true, showSystemUi = false)
@Composable
private fun MessageBubbleErrorPreview() {
    AgentTheme {
        MessageBubble(
            message = ChatMessage(
                id = "preview_err",
                role = MessageRole.ASSISTANT,
                isError = true,
                errorMessage = "请求超时，请重试",
            ),
            onClarifySend = {}
        )
    }
}
