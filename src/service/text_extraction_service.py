import base64
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Union
from loguru import logger

import requests


@dataclass
class ExtractionResult:
    """Data class to store extraction results"""
    file_path: str
    extracted_text: Optional[str]
    error: Optional[str] = None
    task_id: Optional[str] = None


class TextExtractionService:
    _PROMPT = """
    Usted es un especialista en el aprendizaje de idiomas encargado de extraer y analizar el contenido de la página de un libro de texto. Analice el contenido proporcionado prestando especial atención a los siguientes aspectos:

Elementos clave del contenido que debe identificar:
1. Objetivos de aprendizaje
   - Objetivos de la lección claramente establecidos
   - Habilidades lingüísticas objetivo (leer, escribir, hablar, escuchar)
   - Indicadores de nivel de competencia previstos

2. Vocabulario
   - Palabras y frases nuevas
   - Formas y variaciones de palabras
   - Ejemplos contextuales
   - Traducciones o definiciones, si se facilitan
   - Familias de palabras o términos relacionados

3. Puntos gramaticales
   - Estructuras gramaticales
   - Explicaciones de reglas
   - Patrones de uso
   - Excepciones comunes
   - Tablas o patrones de conjugación

4. Ejercicios prácticos
   - Tipos de ejercicios y sus objetivos
   - Instrucciones y ejemplos
   - Claves de respuestas o soluciones, si existen
   - Niveles de dificultad, si se indican

5. Notas culturales
   - Contexto cultural y explicaciones
   - Variaciones regionales
   - Uso en diferentes situaciones
   - Lo que se debe y no se debe hacer culturalmente

6. Elementos multimedia
   - Referencias a materiales de audio
   - Enlaces a recursos en línea
   - Códigos QR o contenidos digitales
   - Ayudas visuales y su finalidad

7. Estructura pedagógica
   - Organización de las secciones
   - Progresión del aprendizaje
   - Secciones de repaso
   - Referencias cruzadas a otros capítulos
   
Instrucciones especiales:
- Conserve todo el formato que indique elementos lingüísticos (negrita, cursiva, subrayado)
- Conserve el texto exacto de las frases y diálogos de ejemplo
- Anote los símbolos o marcadores especiales utilizados para la pronunciación
- Identifique las referencias cruzadas a otras secciones o materiales.
- Señale posibles errores o incoherencias en el contenido.
- Conservar la numeración y seccionamiento de los ejercicios
- Anote cualquier indicador de nivel o marcador de dificultad

Si encuentra contenidos poco claros o ambiguos
1. Anote la ambigüedad en un campo de «notas»
2. Proporcione la interpretación más probable basándose en el contexto
3. 3. Marcarlo para revisión humana si es crítico para el aprendizaje.

Recuerde que este contenido se utilizará para el aprendizaje de idiomas, por lo que la precisión y el detalle son cruciales para una enseñanza adecuada.
Formatea la respuesta en markdown o texto sin formato. No escriba nada más
"""

    def __init__(
            self,
            base_url: str = "http://localhost:8000",
            model: str = "llama3.1",
            strategy: str = "llama_vision",
            storage_profile: str = "default",
            ocr_cache: bool = True
    ):
        """
        Initialize the Text Extraction Service

        Args:
            base_url: Base URL for the OCR service
            model: Model to use for extraction
            strategy: OCR strategy to use
            storage_profile: Storage profile to use
            ocr_cache: Whether to use OCR caching
        """
        self.base_url = base_url.rstrip('/')
        self.model = model
        self.strategy = strategy
        self.storage_profile = storage_profile
        self.ocr_cache = ocr_cache

        # API endpoints
        self.upload_url = f"{self.base_url}/ocr/upload"
        self.request_url = f"{self.base_url}/ocr/request"
        self.result_url = f"{self.base_url}/ocr/result"

    def extract_text(
            self,
            file_paths: Union[str, List[str]],
            prompt: Optional[str] = None,
            prompt_file: Optional[str] = None,
            storage_filename: Optional[str] = None,
            print_progress: bool = False
    ) -> Union[ExtractionResult, List[ExtractionResult]]:
        """
        Extract text from one or multiple PDF files

        Args:
            file_paths: Single file path or list of file paths
            prompt: Optional prompt for the model
            prompt_file: Optional path to prompt file
            storage_filename: Optional storage filename
            print_progress: Whether to print progress

        Returns:
            Single ExtractionResult or list of ExtractionResults
        """
        logger.debug(f"Extracting text from file(s): {file_paths}")
        # Handle single file path
        if isinstance(file_paths, str):
            return self._process_single_file(
                file_paths,
                prompt,
                prompt_file,
                storage_filename,
                print_progress
            )

        # Handle multiple file paths
        results = []
        for file_path in file_paths:
            result = self._process_single_file(
                file_path,
                prompt,
                prompt_file,
                storage_filename,
                print_progress
            )
            results.append(result)

        return results

    def _process_single_file(
            self,
            file_path: str,
            prompt: Optional[str],
            prompt_file: Optional[str],
            storage_filename: Optional[str],
            print_progress: bool
    ) -> ExtractionResult:
        """Process a single file and return its extraction result"""
        try:
            # Read prompt file if provided
            if prompt_file:
                try:
                    prompt = Path(prompt_file).read_text()
                except FileNotFoundError:
                    return ExtractionResult(
                        file_path=file_path,
                        extracted_text=None,
                        error=f"Prompt file not found: {prompt_file}"
                    )

            # Try file upload first
            result = self._upload_file(file_path, prompt, storage_filename)

            # If upload fails, try request method
            if result is None:
                result = self._request_file(file_path, prompt, storage_filename)

            # If both methods fail, return error
            if result is None:
                return ExtractionResult(
                    file_path=file_path,
                    extracted_text=None,
                    error="Failed to process file using both upload and request methods"
                )

            # If we got direct text response
            if result.get('text'):
                return ExtractionResult(
                    file_path=file_path,
                    extracted_text=result['text']
                )

            # If we got a task ID, wait for the result
            task_id = result.get('task_id')
            if task_id:
                text_result = self._get_result(task_id, print_progress)
                return ExtractionResult(
                    file_path=file_path,
                    extracted_text=text_result,
                    task_id=task_id
                )

        except Exception as e:
            return ExtractionResult(
                file_path=file_path,
                extracted_text=None,
                error=str(e)
            )

    def _upload_file(
            self,
            file_path: str,
            prompt: Optional[str],
            storage_filename: Optional[str]
    ) -> Optional[Dict]:
        """Upload file using multipart form data"""
        try:
            with open(file_path, 'rb') as f:
                files = {'file': f}
                data = {
                    'ocr_cache': self.ocr_cache,
                    'model': self.model,
                    'strategy': self.strategy,
                    'storage_profile': self.storage_profile
                }

                if storage_filename:
                    data['storage_filename'] = storage_filename
                if prompt:
                    data['prompt'] = self._PROMPT

                response = requests.post(self.upload_url, files=files, data=data)
                if response.status_code == 200:
                    return response.json()
                return None
        except Exception:
            return None

    def _request_file(
            self,
            file_path: str,
            prompt: Optional[str],
            storage_filename: Optional[str]
    ) -> Optional[Dict]:
        """Upload file using base64 encoded request"""
        try:
            with open(file_path, 'rb') as f:
                file_content = base64.b64encode(f.read()).decode('utf-8')

                data = {
                    'ocr_cache': self.ocr_cache,
                    'model': self.model,
                    'strategy': self.strategy,
                    'storage_profile': self.storage_profile,
                    'file': file_content
                }

                if storage_filename:
                    data['storage_filename'] = storage_filename
                if prompt:
                    data['prompt'] = self._PROMPT

                response = requests.post(self.request_url, json=data)
                if response.status_code == 200:
                    return response.json()
                return None
        except Exception:
            return None

    def _get_result(self, task_id: str, print_progress: bool) -> Optional[str]:
        """Get result for a given task ID"""
        extracted_text_printed = False

        while True:
            response = requests.get(f"{self.result_url}/{task_id}")
            if response.status_code != 200:
                return None

            result = response.json()

            if print_progress and result['state'] != 'SUCCESS':
                task_info = result.get('info', {})
                if task_info.get('extracted_text') and not extracted_text_printed:
                    extracted_text_printed = True
                    logger.debug(f"Extracted text: {task_info['extracted_text']}")
            if result['state'] == 'SUCCESS':
                logger.debug(f"Extraction result: {result['result']}")
                return result['result']
            elif result['state'] == 'FAILURE':
                logger.error(f"Extraction failed: {result['info']}")
                return None

            time.sleep(1)
