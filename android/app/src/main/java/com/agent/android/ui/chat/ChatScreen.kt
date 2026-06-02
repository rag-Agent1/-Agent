package com.agent.android.ui.chat

import android.net.Uri
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.spring
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.interaction.collectIsPressedAsState
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
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
import androidx.compose.material.icons.filled.Send
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material.icons.outlined.SmartToy
import androidx.compose.material.icons.outlined.WifiOff
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
import androidx.compose.material3.TextField
import androidx.compose.material3.TextFieldDefaults
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
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.sp
import androidx.lifecycle.viewmodel.compose.viewModel
import coil.compose.AsyncImage
import com.agent.android.data.SessionManager
import com.agent.android.data.model.Candidate
import com.agent.android.data.model.ChatMessage
import com.agent.android.data.model.Citation
import com.agent.android.data.model.ConnectionStatus
import com.agent.android.data.model.MessageRole
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

    val galleryLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.GetContent()
    ) { uri: Uri? ->
        uri?.let { viewModel.onImageSelected(it) }
    }

    val cameraLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.TakePicture()
    ) { success ->
        if (success && imagePickerState.cameraUri != null) {
            viewModel.onImageSelected(imagePickerState.cameraUri!!)
        }
    }

    val cameraPermissionLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.RequestPermission()
    ) { granted ->
        if (granted && imagePickerState.cameraUri != null) {
            try {
                cameraLauncher.launch(imagePickerState.cameraUri!!)
            } catch (_: Exception) {
                viewModel.clearSelectedImage()
            }
        }
    }

    LaunchedEffect(state.messages.size, state.isStreaming) {
        if (state.messages.isNotEmpty()) {
            listState.animateScrollToItem(state.messages.size - 1)
        }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Text("AI导购", fontWeight = FontWeight.SemiBold)
                    }
                },
                actions = {
                    ConnectionIndicator(state.connectionStatus)
                    IconButton(onClick = { viewModel.newSession() }) {
                        Icon(Icons.Default.Add, contentDescription = "新会话",
                            tint = MaterialTheme.colorScheme.onSurface)
                    }
                    IconButton(onClick = onOpenSettings) {
                        Icon(Icons.Default.Settings, contentDescription = "设置",
                            tint = MaterialTheme.colorScheme.onSurface)
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = MaterialTheme.colorScheme.background
                )
            )
        },
        bottomBar = {
            if (state.messages.isNotEmpty()) {
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
        }
    ) { padding ->
        Box(modifier = Modifier.fillMaxSize().padding(padding)) {
            if (state.messages.isEmpty()) {
                EmptyState(
                    selectedImageUri = state.selectedImageUri,
                    onPickImage = { showImagePicker = true },
                    onClearImage = { viewModel.clearSelectedImage() },
                    onSendMessage = { text ->
                        viewModel.sendMessage(context, text.ifBlank { null })
                    }
                )
            } else {
                LazyColumn(
                    state = listState,
                    modifier = Modifier.fillMaxSize(),
                    contentPadding = PaddingValues(horizontal = 12.dp, vertical = 10.dp),
                    verticalArrangement = Arrangement.spacedBy(14.dp)
                ) {
                    items(state.messages, key = { it.id }) { message ->
                        MessageBubble(
                            message = message,
                            onClarifySend = { viewModel.sendClarification(it) }
                        )
                    }
                }
            }

            state.error?.let { error ->
                ErrorSnackbar(
                    message = error,
                    onDismiss = { viewModel.clearError() },
                    onRetry = { viewModel.retryLastMessage(context) },
                    modifier = Modifier
                        .align(Alignment.BottomCenter)
                        .padding(horizontal = 12.dp, vertical = 8.dp)
                )
            }
        }
    }

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
            .padding(end = 4.dp)
            .size(7.dp)
            .clip(CircleShape)
            .background(color)
    )
}

@Composable
private fun EmptyState(
    selectedImageUri: Uri? = null,
    onPickImage: () -> Unit = {},
    onClearImage: () -> Unit = {},
    onSendMessage: (String) -> Unit = {}
) {
    val gradientBrush = Brush.verticalGradient(
        colors = listOf(
            Color(0xFFE8F0FE),
            Color(0xFFEDE9FE),
            Color(0xFFF3F0ED),
        )
    )

    var text by remember { mutableStateOf("") }

    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(gradientBrush)
    ) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(horizontal = 32.dp)
                .align(Alignment.Center),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Spacer(Modifier.weight(1f))

            // Tagline
            Text(
                "买对不贵，直达好物",
                style = MaterialTheme.typography.titleLarge,
                fontWeight = FontWeight.Normal,
                color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.35f),
                letterSpacing = 3.sp
            )

            Spacer(Modifier.height(28.dp))

            // Minimal input
            Surface(
                shape = RoundedCornerShape(20.dp),
                color = Color.White,
                shadowElevation = 1.dp
            ) {
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    modifier = Modifier.padding(horizontal = 16.dp, vertical = 2.dp)
                ) {
                    TextField(
                        value = text,
                        onValueChange = { text = it },
                        modifier = Modifier.weight(1f).heightIn(min = 44.dp),
                        placeholder = {
                            Text("搜索商品",
                                style = MaterialTheme.typography.bodyLarge,
                                color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.2f))
                        },
                        textStyle = MaterialTheme.typography.bodyLarge.copy(
                            color = MaterialTheme.colorScheme.onSurface,
                            letterSpacing = 0.5.sp
                        ),
                        singleLine = true,
                        colors = TextFieldDefaults.colors(
                            focusedIndicatorColor = Color.Transparent,
                            unfocusedIndicatorColor = Color.Transparent,
                            focusedContainerColor = Color.Transparent,
                            unfocusedContainerColor = Color.Transparent
                        )
                    )
                    if (text.isBlank()) {
                        Box(
                            modifier = Modifier
                                .width(1.5.dp)
                                .height(18.dp)
                                .background(
                                    MaterialTheme.colorScheme.primary.copy(alpha = 0.2f),
                                    RoundedCornerShape(1.dp)
                                )
                        )
                    }
                    Spacer(Modifier.width(4.dp))
                    val canSend = text.isNotBlank() || selectedImageUri != null
                    Surface(
                        onClick = {
                            onSendMessage(text)
                            text = ""
                        },
                        shape = CircleShape,
                        color = if (canSend) MaterialTheme.colorScheme.primary
                                else Color.Transparent
                    ) {
                        Box(
                            modifier = Modifier.size(36.dp),
                            contentAlignment = Alignment.Center
                        ) {
                            Icon(
                                Icons.Default.Send,
                                contentDescription = "发送",
                                tint = if (canSend) MaterialTheme.colorScheme.onPrimary
                                       else MaterialTheme.colorScheme.outline.copy(alpha = 0.3f),
                                modifier = Modifier.size(18.dp)
                            )
                        }
                    }
                }
            }

            // Selected image preview
            if (selectedImageUri != null) {
                Spacer(Modifier.height(16.dp))
                Surface(
                    shape = RoundedCornerShape(12.dp),
                    color = Color.White,
                    shadowElevation = 1.dp
                ) {
                    Row(
                        verticalAlignment = Alignment.CenterVertically,
                        modifier = Modifier.padding(8.dp)
                    ) {
                        AsyncImage(
                            model = selectedImageUri,
                            contentDescription = null,
                            modifier = Modifier
                                .size(48.dp)
                                .clip(RoundedCornerShape(8.dp)),
                            contentScale = ContentScale.Crop
                        )
                        Spacer(Modifier.width(12.dp))
                        Text(
                            "1 张图片已选择",
                            style = MaterialTheme.typography.bodyMedium,
                            color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.4f)
                        )
                        Spacer(Modifier.weight(1f))
                        IconButton(onClick = onClearImage) {
                            Icon(Icons.Default.Close, contentDescription = "清除",
                                tint = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.3f),
                                modifier = Modifier.size(18.dp))
                        }
                    }
                }
            } else {
                Spacer(Modifier.height(24.dp))

                // Camera entry
                Surface(
                    onClick = onPickImage,
                    shape = CircleShape,
                    color = Color.White.copy(alpha = 0.5f)
                ) {
                    Box(modifier = Modifier.size(44.dp), contentAlignment = Alignment.Center) {
                        Icon(
                            Icons.Default.CameraAlt,
                            contentDescription = "拍照",
                            tint = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.3f),
                            modifier = Modifier.size(20.dp)
                        )
                    }
                }
            }

            Spacer(Modifier.weight(1f))
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
        Column(modifier = Modifier.padding(horizontal = 12.dp, vertical = 8.dp)) {
            selectedImageUri?.let { uri ->
                Row(
                    modifier = Modifier.fillMaxWidth().padding(bottom = 8.dp),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    AsyncImage(
                        model = uri,
                        contentDescription = "已选图片",
                        modifier = Modifier
                            .size(44.dp)
                            .clip(RoundedCornerShape(8.dp)),
                        contentScale = ContentScale.Crop
                    )
                    IconButton(onClick = onClearImage) {
                        Icon(Icons.Default.Close, contentDescription = "清除",
                            tint = MaterialTheme.colorScheme.onSurfaceVariant)
                    }
                }
            }

            if (isUploading) {
                LinearProgressIndicator(
                    modifier = Modifier.fillMaxWidth().padding(bottom = 8.dp),
                    color = MaterialTheme.colorScheme.primary.copy(alpha = 0.3f),
                    trackColor = MaterialTheme.colorScheme.outline.copy(alpha = 0.15f)
                )
            }

            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically
            ) {
                IconButton(onClick = onPickImage) {
                    Icon(
                        Icons.Default.CameraAlt,
                        contentDescription = "拍照/选图",
                        tint = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f)
                    )
                }

                OutlinedTextField(
                    value = text,
                    onValueChange = onTextChange,
                    modifier = Modifier.weight(1f),
                    placeholder = {
                        Text("输入消息...",
                            color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.35f))
                    },
                    singleLine = true,
                    shape = RoundedCornerShape(24.dp),
                    colors = OutlinedTextFieldDefaults.colors(
                        focusedBorderColor = MaterialTheme.colorScheme.outline.copy(alpha = 0.5f),
                        unfocusedBorderColor = MaterialTheme.colorScheme.outline.copy(alpha = 0.25f),
                        focusedContainerColor = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.4f),
                        unfocusedContainerColor = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.4f)
                    )
                )

                Spacer(Modifier.width(6.dp))

                if (isStreaming) {
                    Surface(
                        shape = CircleShape,
                        color = Color.Transparent,
                        modifier = Modifier.size(40.dp)
                    ) {
                        IconButton(onClick = onStop) {
                            Icon(
                                Icons.Default.Stop,
                                contentDescription = "停止",
                                tint = MaterialTheme.colorScheme.error,
                                modifier = Modifier.size(20.dp)
                            )
                        }
                    }
                } else {
                    val canSend = text.isNotBlank() || selectedImageUri != null
                    Surface(
                        shape = CircleShape,
                        color = if (canSend)
                            MaterialTheme.colorScheme.primary
                        else
                            MaterialTheme.colorScheme.outline.copy(alpha = 0.15f),
                        modifier = Modifier.size(40.dp)
                    ) {
                        IconButton(
                            onClick = onSend,
                            enabled = canSend
                        ) {
                            Icon(
                                Icons.Default.Send,
                                contentDescription = "发送",
                                tint = if (canSend) MaterialTheme.colorScheme.onPrimary
                                       else MaterialTheme.colorScheme.outline,
                                modifier = Modifier.size(18.dp)
                            )
                        }
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

    Column(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 2.dp),
        horizontalAlignment = alignment
    ) {
        // User image - shown before the bubble
        if (message.imageLocalUri != null && isUser) {
            Surface(
                shape = RoundedCornerShape(12.dp),
                color = MaterialTheme.colorScheme.surfaceVariant,
                modifier = Modifier.size(112.dp)
            ) {
                AsyncImage(
                    model = message.imageLocalUri,
                    contentDescription = "用户图片",
                    modifier = Modifier.clip(RoundedCornerShape(12.dp)),
                    contentScale = ContentScale.Crop
                )
            }
            Spacer(Modifier.height(6.dp))
        }

        // Bot avatar for assistant messages
        if (!isUser) {
            Row(verticalAlignment = Alignment.Top) {
                Surface(
                    shape = CircleShape,
                    color = MaterialTheme.colorScheme.primary.copy(alpha = 0.08f),
                    modifier = Modifier.size(32.dp)
                ) {
                    Box(contentAlignment = Alignment.Center) {
                        Icon(
                            Icons.Outlined.SmartToy,
                            contentDescription = null,
                            modifier = Modifier.size(18.dp),
                            tint = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.4f)
                        )
                    }
                }
                Spacer(Modifier.width(10.dp))
                BubbleContent(message = message, isUser = false, onClarifySend = onClarifySend)
            }
        } else {
            BubbleContent(message = message, isUser = true, onClarifySend = onClarifySend)
        }
    }
}

@Composable
private fun BubbleContent(
    message: ChatMessage,
    isUser: Boolean,
    onClarifySend: (String) -> Unit
) {
    val bgColor = if (isUser)
        MaterialTheme.colorScheme.primary.copy(alpha = 0.08f)
    else
        MaterialTheme.colorScheme.surface

    val hasContent = message.text.isNotBlank() ||
            !message.candidates.isNullOrEmpty() ||
            !message.citations.isNullOrEmpty() ||
            message.isLoading || message.isError

    if (!hasContent && message.role == MessageRole.USER) return

    Column(modifier = Modifier.widthIn(max = 300.dp)) {
        Surface(
            shape = RoundedCornerShape(
                topStart = 16.dp,
                topEnd = 16.dp,
                bottomStart = if (isUser) 16.dp else 4.dp,
                bottomEnd = if (isUser) 4.dp else 16.dp
            ),
            color = bgColor,
            shadowElevation = if (isUser) 0.dp else 1.dp
        ) {
            Column(modifier = Modifier.padding(14.dp)) {
                // Candidates
                if (!message.candidates.isNullOrEmpty()) {
                    CandidateCardRow(message.candidates)
                    Spacer(Modifier.height(10.dp))
                }

                // Loading skeleton
                if (message.isLoading && !message.isStreaming) {
                    Text("正在搜索...",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.45f),
                        modifier = Modifier.padding(bottom = 8.dp))
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        repeat(3) { SkeletonCard() }
                    }
                }

                // Text
                if (message.text.isNotBlank()) {
                    Text(
                        text = message.text,
                        color = if (isUser) MaterialTheme.colorScheme.onSurface
                                else MaterialTheme.colorScheme.onSurface,
                        style = MaterialTheme.typography.bodyMedium,
                        lineHeight = 22.sp
                    )
                }

                // Citations
                if (!message.citations.isNullOrEmpty()) {
                    Spacer(Modifier.height(8.dp))
                    CitationSection(message.citations)
                }

                // Error
                if (message.isError) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Icon(
                            Icons.Outlined.WifiOff,
                            contentDescription = null,
                            modifier = Modifier.size(14.dp),
                            tint = MaterialTheme.colorScheme.error
                        )
                        Spacer(Modifier.width(4.dp))
                        Text(
                            text = message.errorMessage ?: "出错了",
                            color = MaterialTheme.colorScheme.error,
                            style = MaterialTheme.typography.bodySmall
                        )
                    }
                }
            }
        }

        // Clarify
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
            color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.5f),
            fontWeight = FontWeight.Medium,
            modifier = Modifier.padding(bottom = 8.dp)
        )
        LazyRow(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            items(candidates) { candidate ->
                CandidateCard(candidate)
            }
        }
    }
}

@Composable
private fun CandidateCard(candidate: Candidate) {
    var showDetail by remember { mutableStateOf(false) }
    val interactionSource = remember { MutableInteractionSource() }
    val isPressed by interactionSource.collectIsPressedAsState()
    val scale by animateFloatAsState(
        targetValue = if (isPressed) 0.96f else 1f,
        animationSpec = spring(stiffness = 450f, dampingRatio = 0.5f)
    )

    Card(
        modifier = Modifier
            .width(148.dp)
            .graphicsLayer(scaleX = scale, scaleY = scale)
            .clickable(
                interactionSource = interactionSource,
                indication = null,
                onClick = { showDetail = true }
            ),
        shape = RoundedCornerShape(14.dp),
        elevation = CardDefaults.cardElevation(
            defaultElevation = if (isPressed) 3.dp else 1.dp
        ),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)
    ) {
        Column {
            Box {
                AsyncImage(
                    model = candidate.imageUrl,
                    contentDescription = candidate.title,
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(124.dp)
                        .clip(RoundedCornerShape(topStart = 14.dp, topEnd = 14.dp)),
                    contentScale = ContentScale.Crop
                )
                Surface(
                    color = scoreColor(candidate.score).copy(alpha = 0.9f),
                    shape = RoundedCornerShape(bottomStart = 8.dp),
                    modifier = Modifier.align(Alignment.TopEnd)
                ) {
                    Text(
                        "${(candidate.score * 100).toInt()}%",
                        modifier = Modifier.padding(horizontal = 6.dp, vertical = 3.dp),
                        color = Color.White,
                        fontSize = 11.sp,
                        fontWeight = FontWeight.SemiBold
                    )
                }
            }
            Column(modifier = Modifier.padding(10.dp)) {
                Text(
                    candidate.title,
                    style = MaterialTheme.typography.bodySmall,
                    maxLines = 2,
                    overflow = TextOverflow.Ellipsis,
                    color = MaterialTheme.colorScheme.onSurface,
                    fontWeight = FontWeight.Medium
                )
                if (candidate.price != null) {
                    Spacer(Modifier.height(3.dp))
                    Text(
                        "¥${candidate.price}",
                        style = MaterialTheme.typography.labelLarge,
                        color = MaterialTheme.colorScheme.primary,
                        fontWeight = FontWeight.SemiBold
                    )
                }
            }
        }
    }

    if (showDetail) {
        CandidateDetailSheet(candidate = candidate, onDismiss = { showDetail = false })
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun CandidateDetailSheet(candidate: Candidate, onDismiss: () -> Unit) {
    val sheetState = rememberModalBottomSheetState()
    ModalBottomSheet(
        onDismissRequest = onDismiss,
        sheetState = sheetState,
        containerColor = MaterialTheme.colorScheme.surface
    ) {
        Column(modifier = Modifier.padding(20.dp)) {
            AsyncImage(
                model = candidate.imageUrl,
                contentDescription = candidate.title,
                modifier = Modifier
                    .fillMaxWidth()
                    .height(240.dp)
                    .clip(RoundedCornerShape(12.dp)),
                contentScale = ContentScale.Crop
            )
            Spacer(Modifier.height(16.dp))
            Text(candidate.title, style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.SemiBold)
            if (candidate.price != null) {
                Spacer(Modifier.height(4.dp))
                Text("¥${candidate.price}",
                    style = MaterialTheme.typography.headlineMedium,
                    fontWeight = FontWeight.Bold,
                    color = MaterialTheme.colorScheme.primary)
            }
            Spacer(Modifier.height(8.dp))
            Text("相似度: ${(candidate.score * 100).toInt()}%",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f))
            candidate.attrs?.let { attrs ->
                Spacer(Modifier.height(16.dp))
                Text("关键属性", style = MaterialTheme.typography.titleSmall,
                    fontWeight = FontWeight.Medium)
                Spacer(Modifier.height(6.dp))
                attrs.forEach { (key, value) ->
                    Row(modifier = Modifier.padding(vertical = 2.dp)) {
                        Text("$key: ", style = MaterialTheme.typography.bodyMedium,
                            fontWeight = FontWeight.Medium,
                            color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f))
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
            Icon(
                if (expanded) Icons.Default.ExpandLess else Icons.Default.ExpandMore,
                contentDescription = null,
                modifier = Modifier.size(16.dp),
                tint = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.4f)
            )
            Spacer(Modifier.width(4.dp))
            Text(
                "引用来源 (${citations.size})",
                style = MaterialTheme.typography.labelSmall,
                color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.45f)
            )
        }

        AnimatedVisibility(visible = expanded, enter = fadeIn(), exit = fadeOut()) {
            Column {
                citations.forEachIndexed { index, citation ->
                    CitationItem(index + 1, citation)
                    if (index < citations.size - 1) {
                        HorizontalDivider(
                            modifier = Modifier.padding(vertical = 6.dp),
                            color = MaterialTheme.colorScheme.outline.copy(alpha = 0.15f)
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun CitationItem(index: Int, citation: Citation) {
    Column(modifier = Modifier.padding(start = 4.dp)) {
        Text(
            "[$index] ${citation.source}",
            style = MaterialTheme.typography.labelSmall,
            fontWeight = FontWeight.Medium,
            color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.55f)
        )
        Spacer(Modifier.height(2.dp))
        Text(
            "\"${citation.snippet}\"",
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.5f)
        )
    }
}

@Composable
private fun ClarifySection(question: String, onSend: (String) -> Unit) {
    var input by remember { mutableStateOf("") }

    Surface(
        shape = RoundedCornerShape(12.dp),
        color = MaterialTheme.colorScheme.primary.copy(alpha = 0.06f)
    ) {
        Column(modifier = Modifier.padding(14.dp)) {
            Text(
                question,
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurface,
                fontWeight = FontWeight.Medium
            )
            Spacer(Modifier.height(10.dp))
            Row(verticalAlignment = Alignment.CenterVertically) {
                OutlinedTextField(
                    value = input,
                    onValueChange = { input = it },
                    modifier = Modifier.weight(1f),
                    placeholder = {
                        Text("请输入...",
                            color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.35f))
                    },
                    singleLine = true,
                    shape = RoundedCornerShape(20.dp),
                    colors = OutlinedTextFieldDefaults.colors(
                        focusedBorderColor = MaterialTheme.colorScheme.outline.copy(alpha = 0.4f),
                        unfocusedBorderColor = MaterialTheme.colorScheme.outline.copy(alpha = 0.2f)
                    )
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
        modifier = modifier,
        shape = RoundedCornerShape(12.dp),
        color = MaterialTheme.colorScheme.errorContainer,
        shadowElevation = 4.dp
    ) {
        Row(
            modifier = Modifier.padding(horizontal = 14.dp, vertical = 10.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Icon(
                Icons.Outlined.WifiOff,
                contentDescription = null,
                modifier = Modifier.size(16.dp),
                tint = MaterialTheme.colorScheme.onErrorContainer
            )
            Spacer(Modifier.width(8.dp))
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
        modifier = Modifier.width(148.dp),
        shape = RoundedCornerShape(14.dp),
        elevation = CardDefaults.cardElevation(defaultElevation = 0.dp),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.5f)
        )
    ) {
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .height(124.dp)
                .background(MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.3f))
        )
        Column(modifier = Modifier.padding(10.dp)) {
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .height(10.dp)
                    .clip(RoundedCornerShape(4.dp))
                    .background(MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.4f))
            )
            Spacer(Modifier.height(6.dp))
            Box(
                modifier = Modifier
                    .width(60.dp)
                    .height(10.dp)
                    .clip(RoundedCornerShape(4.dp))
                    .background(MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.4f))
            )
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

// ==================== Previews ====================

private val mockCandidates = listOf(
    Candidate("SKU001", 0.92, "索尼 WH-1000XM5 无线降噪耳机", "https://picsum.photos/seed/sku1/200", mapOf("品牌" to "索尼", "颜色" to "黑色"), 2999.0),
    Candidate("SKU002", 0.87, "Bose QC45 无线降噪耳机", "https://picsum.photos/seed/sku2/200", mapOf("品牌" to "Bose", "颜色" to "银色"), 2499.0),
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
            EmptyState(onPickImage = {}, onClearImage = {}, onSendMessage = {})
        }
    }
}

@Preview(showBackground = true, showSystemUi = false)
@Composable
private fun ChatBottomBarPreview() {
    AgentTheme {
        ChatBottomBar("", {}, null, false, false, {}, {}, {}, {})
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
private fun CitationSectionPreview() {
    AgentTheme {
        CitationSection(mockCitations)
    }
}

@Preview(showBackground = true, showSystemUi = false)
@Composable
private fun ClarifySectionPreview() {
    AgentTheme {
        ClarifySection("您更看重降噪效果还是舒适度？", {})
    }
}

@Preview(showBackground = true, showSystemUi = false)
@Composable
private fun ErrorSnackbarPreview() {
    AgentTheme {
        ErrorSnackbar("无法连接到服务器", {}, {}, Modifier.padding(16.dp))
    }
}

@Preview(showBackground = true, showSystemUi = false)
@Composable
private fun SkeletonCardPreview() {
    AgentTheme {
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            repeat(3) { SkeletonCard() }
        }
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
                text = "根据您拍摄的图片，我推荐这款索尼 WH-1000XM5 耳机。",
                candidates = mockCandidates,
                citations = mockCitations,
                isLoading = false,
                isStreaming = false,
            ),
            onClarifySend = {}
        )
    }
}
