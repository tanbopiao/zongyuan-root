import gradio as gr

with gr.Blocks(title="Zongyuan Dataset Card") as demo:
    gr.Markdown("# Zongyuan Dataset Card")
    gr.Markdown("ModelScope / AtomGit dataset demo template")
    gr.Markdown("---")
    gr.HTML('<a href="https://aios.huodouai.com" target="_blank" style="padding:10px 20px;background:#4F46E5;color:white;border-radius:6px;text-decoration:none;">访问产品站</a>')
    gr.Markdown("*Apache-2.0*")

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)
