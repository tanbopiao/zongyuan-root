
with open("/www/wwwroot/aios.huodouai.com/chat.html", "r") as f:
    content = f.read()

# 新的sendMessage函数（流式版本）
old_function = """        async function sendMessage() {
            const text = inputBox.value.trim();
            if (!text) return;

            // 添加用户消息
            addMessage(text, 'user');
            inputBox.value = '';
            inputBox.style.height = 'auto';
            sendBtn.disabled = true;

            // 添加机器人输入中
            const botMessageDiv = addMessage('思考中...', 'bot', true);

            try {
                const res = await fetch(API_URL, {
                    method: 'POST',
                    headers: {
                        'Authorization': 'Bearer ' + API_KEY,
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ message: text })
                });

                const data = await res.json();
                botMessageDiv.querySelector('.message-content').innerHTML = marked.parse(data.answer);
            } catch (e) {
                botMessageDiv.querySelector('.message-content').textContent = '抱歉，服务暂时不可用，请稍后再试。';
            } finally {
                sendBtn.disabled = false;
                chatContainer.scrollTop = chatContainer.scrollHeight;
            }
        }"""

new_function = """        async function sendMessage() {
            const text = inputBox.value.trim();
            if (!text) return;

            // 添加用户消息
            addMessage(text, 'user');
            inputBox.value = '';
            inputBox.style.height = 'auto';
            sendBtn.disabled = true;

            // 添加机器人输入中
            const botMessageDiv = addMessage('', 'bot', true);
            const messageContent = botMessageDiv.querySelector('.message-content');
            let fullText = '';

            try {
                const res = await fetch(API_URL + '/stream', {
                    method: 'POST',
                    headers: {
                        'Authorization': 'Bearer ' + API_KEY,
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ message: text })
                });

                const reader = res.body.getReader();
                const decoder = new TextDecoder();

                while (true) {
                    const { done, value } = await reader.read();
                    if (done) break;

                    const chunk = decoder.decode(value);
                    const lines = chunk.split('\\n');

                    for (const line of lines) {
                        if (line.trim()) {
                            try {
                                const data = JSON.parse(line);
                                if (data.choices && data.choices[0].delta.content) {
                                    fullText += data.choices[0].delta.content;
                                    messageContent.innerHTML = marked.parse(fullText);
                                    chatContainer.scrollTop = chatContainer.scrollHeight;
                                }
                            } catch (e) {
                                // 忽略解析错误
                            }
                        }
                    }
                }
            } catch (e) {
                messageContent.textContent = '抱歉，服务暂时不可用，请稍后再试。';
            } finally {
                sendBtn.disabled = false;
                chatContainer.scrollTop = chatContainer.scrollHeight;
            }
        }"""

content = content.replace(old_function, new_function)

with open("/tmp/chat_stream.html", "w") as f:
    f.write(content)
print("✅ 流式输出已添加到对话页面")
