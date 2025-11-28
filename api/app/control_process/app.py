import gradio as gr
import requests
import os

# La URL de la API dentro de la red de Docker
API_URL = "http://api:8000"

def start_training(user_code, config_file):
    if user_code and config_file is not None:
        files = {'file': (os.path.basename(config_file.name), open(config_file.name, 'rb'), 'application/x-yaml')}
        params = {'user_code': user_code}
        try:
            response = requests.post(f"{API_URL}/train/", params=params, files=files)
            response.raise_for_status()  # Lanza un error para respuestas 4xx/5xx
            return response.json()
        except requests.exceptions.RequestException as e:
            return f"Error al conectar con la API: {e}"
    return "Por favor, proporciona un código de usuario y un archivo de configuración."

def evaluate_model(user_code, data_yaml, model_path):
    if user_code and data_yaml and model_path:
        params = {
            'user_code': user_code,
            'data_yaml': data_yaml,
            'model_path': model_path
        }
        try:
            response = requests.post(f"{API_URL}/evaluate/", params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return f"Error al conectar con la API: {e}"
    return "Por favor, completa todos los campos para la evaluación."

with gr.Blocks() as demo:
    gr.Markdown("# Interfaz de Control para `wyoloservice`")

    with gr.Tab("Entrenamiento"):
        gr.Markdown("## Iniciar un nuevo entrenamiento")
        train_user_code = gr.Textbox(label="Código de Usuario")
        config_file = gr.File(label="Archivo de Configuración YAML")
        train_button = gr.Button("Iniciar Entrenamiento")
        train_output = gr.JSON(label="Respuesta de la API")

    with gr.Tab("Evaluación"):
        gr.Markdown("## Evaluar un modelo")
        eval_user_code = gr.Textbox(label="Código de Usuario")
        data_yaml_path = gr.Textbox(label="Ruta al data.yaml", placeholder="/path/to/data.yaml")
        model_path_input = gr.Textbox(label="Ruta al modelo", placeholder="/path/to/model.pt")
        eval_button = gr.Button("Iniciar Evaluación")
        eval_output = gr.JSON(label="Respuesta de la API")

    train_button.click(start_training, inputs=[train_user_code, config_file], outputs=train_output)
    eval_button.click(evaluate_model, inputs=[eval_user_code, data_yaml_path, model_path_input], outputs=eval_output)

if __name__ == "__main__":
    # Escucha en 0.0.0.0 para ser accesible desde fuera del contenedor
    demo.launch(server_name="0.0.0.0", server_port=7860)