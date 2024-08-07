# создаем простое streamlit приложение для работы с вашими pdf-файлами при помощи YaGPT

import streamlit as st
import tempfile
import os
from opensearchpy import OpenSearch
from yandex_chain import YandexEmbeddings
from yandex_chain import YandexLLM


from langchain.prompts import PromptTemplate
from langchain.document_loaders import DirectoryLoader, PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.vectorstores import OpenSearchVectorSearch

from langchain.chains import RetrievalQA
from langchain_community.chat_models import ChatYandexGPT

from streamlit_chat import message

# from dotenv import load_dotenv

ROOT_DIRECTORY = "."
MDB_OS_CA = f"{ROOT_DIRECTORY}/.opensearch/root.crt"

# использовать системные переменные из облака streamlit (secrets)
# yagpt_api_key = st.secrets["yagpt_api_key"]
# yagpt_folder_id = st.secrets["yagpt_folder_id"]
# yagpt_api_id = st.secrets["yagpt_api_id"]
mdb_os_pwd = st.secrets["mdb_os_pwd"]
mdb_os_hosts = st.secrets["mdb_os_hosts"].split(",")
mdb_os_index_name = st.secrets["mdb_os_index_name"]
mdb_prefix = st.secrets["mdb_prefix"]

# MDB_OS_CA = st.secrets["mdb_os_ca"] # 

def ingest_docs(temp_dir: str = tempfile.gettempdir()):
    """
    Инъекция ваших pdf файлов в MBD Opensearch
    """
    try:
        # выдать ошибку, если каких-то переменных не хватает
        if not yagpt_api_key or not yagpt_folder_id or not mdb_os_pwd or not mdb_os_hosts or not mdb_os_index_name or not mdb_prefix:
            raise ValueError(
                "Пожалуйста укажите необходимый набор переменных окружения")

        # загрузить PDF файлы из временной директории
        loader = DirectoryLoader(
            temp_dir, glob="**/*.pdf", loader_cls=PyPDFLoader, recursive=True
        )
        documents = loader.load() 

        # разбиваем документы на блоки
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        documents = text_splitter.split_documents(documents)
        print(len(documents))
        text_to_print = f"Ориентировочное время = {len(documents)} с."
        st.text(text_to_print)

        # подключаемся к базе данных MDB Opensearch, используя наши ключи (проверка подключения)
        conn = OpenSearch(
            mdb_os_hosts,
            http_auth=('admin', mdb_os_pwd),
            use_ssl=True,
            verify_certs=False,
            ca_certs=MDB_OS_CA)
        # для включения проверки MDB сертификата используйте verify_certs=True, также надо будет загрузить сертификат используя инструкцию по ссылке 
        # https://cloud.yandex.ru/docs/managed-opensearch/operations/connect 
        # и положить его в папку .opensearch/root.crt
        
        # инициируем процедуру превращения блоков текста в Embeddings через YaGPT Embeddings API, используя API ключ доступа
        embeddings = YandexEmbeddings(folder_id=yagpt_folder_id, api_key=yagpt_api_key)

        # добавляем "документы" (embeddings) в векторную базу данных Opensearch
        docsearch = OpenSearchVectorSearch.from_documents(
            documents,
            embeddings,
            opensearch_url=mdb_os_hosts,
            http_auth=("admin", mdb_os_pwd),
            use_ssl = True,
            verify_certs = False,
            ca_certs = MDB_OS_CA,
            engine = 'lucene',
            index_name = mdb_os_index_name,
            bulk_size=1000000
        )
    # bulk_size - это максимальное количество embeddings, которое можно будет поместить в индекс

    except Exception as e:
        st.error(f"Возникла ошибка при добавлении ваших файлов: {str(e)}")


# это основная функция, которая запускает приложение streamlit
def main():
    # Загрузка логотипа компании
    logo_image = './images/logo.png'  # Путь к изображению логотипа

    # # Отображение логотипа в основной части приложения
    from PIL import Image
    # Загрузка логотипа
    logo = Image.open(logo_image)
    # Изменение размера логотипа
    resized_logo = logo.resize((100, 100))
    # Отображаем лого измененного небольшого размера
    st.image(resized_logo)
    # Указываем название и заголовок Streamlit приложения
    st.title('YandexGPT чат-бот с вашими PDF файлами')
    # st.title('Игровая площадка на базе YandexGPT для построения Вопрос-Ответных Систем по PDF файлам')
    st.warning('Загружайте свои PDF-файлы и задавайте вопросы по ним. Если вы уже загрузили свои файлы, то ***обязательно*** удалите их из списка загруженных и переходите к чату ниже.')

    # вводить все credentials в графическом интерфейсе слева
    # Sidebar contents
    with st.sidebar:
        st.title('\U0001F917\U0001F4ACИИ-помощник')
        st.markdown('''
        ## О программе
        Чат-бот реализует [Retrieval-Augmented Generation (RAG)](https://github.com/yandex-cloud-examples/yc-yandexgpt-qa-bot-for-docs/blob/main/README.md) подход
        и использует следующие компоненты:
        - [Yandex GPT](https://cloud.yandex.ru/services/yandexgpt)
        - [Yandex GPT for Langchain](https://pypi.org/project/yandex-chain/)
        - [YC MDB Opensearch](https://cloud.yandex.ru/docs/managed-opensearch/)
        - [Streamlit](https://streamlit.io/)
        - [LangChain](https://python.langchain.com/)
        ''')
        st.markdown('''
            ## Дополнительные настройки
            Можно выбрать [модель](https://cloud.yandex.ru/ru/docs/yandexgpt/concepts/models), степень креативности и системный промпт
            ''')

    model_list = [
      "YandexGPT Lite",
      "YandexGPT Pro"      
    ]    
    index_model = 1
    selected_model = st.sidebar.radio("Выберите модель для работы:", model_list, index=index_model, key="index")     
    
    # yagpt_prompt = st.sidebar.text_input("Промпт-инструкция для YaGPT")
    # Добавляем виджет для выбора опции
    prompt_option = st.sidebar.selectbox(
        'Выберите какой системный промпт использовать',
        ('По умолчанию', 'Задать самостоятельно')
    )
    default_prompt = """
    Представь, что ты полезный ИИ-помощник. Твоя задача отвечать на ВОПРОС по информации из предоставленного ниже ДОКУМЕНТА.
    Отвечай точно в рамках предоставленного ДОКУМЕНТА, даже если тебя просят придумать.
    Отвечай вежливо в официальном стиле. 
    Если ответ в ДОКУМЕНТЕ отсутствует, отвечай: "Я могу давать ответы только по тематике загруженных документов. Мне не удалось найти в документах ответ на ваш вопрос." даже если думаешь, что знаешь ответ на вопрос. 
    ДОКУМЕНТ: {context}
    ВОПРОС: {question}
    """
     # Если выбрана опция "Задать самостоятельно", показываем поле для ввода промпта
    if prompt_option == 'Задать самостоятельно':
        custom_prompt = st.sidebar.text_input('Введите пользовательский промпт:')
    else:
        custom_prompt = default_prompt
        # st.sidebar.write(custom_prompt)
        with st.sidebar:
            st.code(custom_prompt)
    # Если выбрали "задать самостоятельно" и не задали, то берем дефолтный промпт
    if len(custom_prompt)==0: custom_prompt = default_prompt  


    global  yagpt_folder_id, yagpt_api_key, mdb_os_ca, mdb_os_pwd, mdb_os_hosts, mdb_os_index_name, mdb_prefix    
    yagpt_folder_id = st.sidebar.text_input("YAGPT_FOLDER_ID", type='password')
    # yagpt_api_id = st.sidebar.text_input("YAGPT_API_ID", type='password')
    yagpt_api_key = st.sidebar.text_input("YAGPT_API_KEY", type='password')
    mdb_os_ca = MDB_OS_CA
    # mdb_os_pwd = st.sidebar.text_input("MDB_OpenSearch_PASSWORD", type='password')
    # mdb_os_hosts = st.sidebar.text_input("MDB_OpenSearch_HOSTS через 'запятую' ", type='password').split(",")
    mdb_os_index_name = st.sidebar.text_input("MDB_OpenSearch_INDEX_NAME", type='password', value=mdb_os_index_name)
    mdb_os_index_name = f"{mdb_prefix}-{mdb_os_index_name}"

    # yagpt_temp = st.sidebar.slider("Температура", 0.0, 1.0, 0.1)
    rag_k = st.sidebar.slider("Количество поисковых выдач размером с один блок", 1, 10, 5)

    # yagpt_temp = st.sidebar.text_input("Температура", type='password', value=0.01)
    # rag_k = st.sidebar.text_input("Количество поисковых выдач размером с один блок", type='password', value=5)
    yagpt_temp = st.sidebar.slider("Степень креативности (температура)", 0.0, 1.0, 0.01)

    # Параметры chunk_size и chunk_overlap
    global chunk_size, chunk_overlap
    chunk_size = st.sidebar.slider("Выберите размер текстового 'окна' разметки документов в символах", 0, 2000, 1000)
    chunk_overlap = st.sidebar.slider("Выберите размер блока перекрытия в символах", 0, 400, 100)

    # Выводим предупреждение, если пользователь не указал свои учетные данные
    if not yagpt_api_key or not yagpt_folder_id or not mdb_os_pwd or not mdb_os_hosts or not mdb_os_index_name or not mdb_prefix:
        st.warning(
            "Пожалуйста, задайте свои учетные данные (в secrets/.env или в раскрывающейся панели слева) для запуска этого приложения.")

    # Загрузка pdf файлов
    uploaded_files = st.file_uploader(
        "После загрузки файлов в формате pdf начнется их добавление в векторную базу данных MDB Opensearch.", accept_multiple_files=True, type=['pdf'])

    # если файлы загружены, сохраняем их во временную папку и потом заносим в vectorstore
    if uploaded_files:
        # создаем временную папку и сохраняем в ней загруженные файлы
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                for uploaded_file in uploaded_files:
                    file_name = uploaded_file.name
                    # сохраняем файл во временную папку
                    with open(os.path.join(temp_dir, file_name), "wb") as f:
                        f.write(uploaded_file.read())
                # отображение спиннера во время инъекции файлов
                with st.spinner("Добавление ваших файлов в базу ..."):
                    ingest_docs(temp_dir)
                    st.success("Ваш(и) файл(ы) успешно принят(ы)")
                    st.session_state['ready'] = True
        except Exception as e:
            st.error(
                f"При загрузке ваших файлов произошла ошибка: {str(e)}")

    # Логика обработки сообщений от пользователей
    # инициализировать историю чата, если ее пока нет 
    if 'chat_history' not in st.session_state:
        st.session_state['chat_history'] = []

    # инициализировать состояние готовности, если его пока нет
    if 'ready' not in st.session_state:
        st.session_state['ready'] = True

    if st.session_state['ready']:

        # подключиться к векторной БД Opensearch, используя учетные данные (проверка подключения)
        conn = OpenSearch(
            mdb_os_hosts,
            http_auth=('admin', mdb_os_pwd),
            use_ssl=True,
            verify_certs=False,
            ca_certs=MDB_OS_CA
            )

        # инициализировать модели YandexEmbeddings и YandexGPT
        embeddings = YandexEmbeddings(folder_id=yagpt_folder_id, api_key=yagpt_api_key)

        # model_uri = "gpt://"+str(yagpt_folder_id)+"/yandexgpt/latest"
        # model_uri = "gpt://"+str(yagpt_folder_id)+"/yandexgpt-lite/latest"
        if selected_model==model_list[0]: 
            model_uri = "gpt://"+str(yagpt_folder_id)+"/yandexgpt-lite/latest"
        else:
            model_uri = "gpt://"+str(yagpt_folder_id)+"/yandexgpt/latest"  
        # обращение к модели YaGPT
        llm = ChatYandexGPT(api_key=yagpt_api_key, model_uri=model_uri, temperature = yagpt_temp, max_tokens=8000)
        # model = YandexLLM(api_key = yagpt_api_key, folder_id = yagpt_folder_id, temperature = 0.6, max_tokens=8000, use_lite = False)
        # llm = YandexLLM(api_key=yagpt_api_key, folder_id=yagpt_folder_id, temperature = yagpt_temp, max_tokens=7000)
        # llm = YandexLLM(api_key = yagpt_api_key, folder_id = yagpt_folder_id, temperature = yagpt_temp.6, max_tokens=8000, use_lite = False)

        # инициализация retrival chain - цепочки поиска
        vectorstore = OpenSearchVectorSearch (
            embedding_function=embeddings,
            index_name = mdb_os_index_name,
            opensearch_url=mdb_os_hosts,
            http_auth=("admin", mdb_os_pwd),
            use_ssl = True,
            verify_certs = False,
            ca_certs = MDB_OS_CA,
            engine = 'lucene'
        )  

        # template = """
        # Представь, что ты полезный ИИ-помощник. Твоя задача отвечать на вопросы по информации из предоставленного ниже контекста.
        # Отвечай точно в рамках предоставленного контекста, даже если тебя просят придумать.
        # Отвечай вежливо в официальном стиле. 
        # Если ответ в контексте отсутствует, отвечай: "Я могу давать ответы только по тематике загруженных документов. Мне не удалось найти в документах ответ на ваш вопрос." даже если думаешь, что знаешь ответ на вопрос. 
        # Контекст: {context}
        # Вопрос: {question}
        # """
        QA_CHAIN_PROMPT = PromptTemplate.from_template(custom_prompt)
        qa = RetrievalQA.from_chain_type(
            llm,
            retriever=vectorstore.as_retriever(search_kwargs={'k': rag_k}),
            return_source_documents=True,
            chain_type_kwargs={"prompt": QA_CHAIN_PROMPT}
        )

        if 'generated' not in st.session_state:
            st.session_state['generated'] = [
                "Что бы вы хотели узнать?"]

        if 'past' not in st.session_state:
            st.session_state['past'] = ["Привет!"]

        # контейнер для истории чата
        response_container = st.container()

        # контейнер для текстового поля
        container = st.container()

        with container:
            with st.form(key='my_form', clear_on_submit=True):
                user_input = st.text_input(
                    "Вопрос:", placeholder="О чем этот документ?", key='input')
                submit_button = st.form_submit_button(label='Отправить')

            if submit_button and user_input:
                # отобразить загрузочный "волчок"
                with st.spinner("Думаю..."):
                    print("История чата: ", st.session_state['chat_history'])
                    output = qa(
                        {"query": user_input})
                    print(output)
                    st.session_state['past'].append(user_input)
                    st.session_state['generated'].append(output['result'])

                    # # обновляем историю чата с помощью вопроса пользователя и ответа от бота
                    st.session_state['chat_history'].append(
                        {"вопрос": user_input, "ответ": output['result']})
                    ## добавляем источники к ответу
                    input_documents = output['source_documents']
                    i = 0
                    for doc in input_documents:
                        source = doc.metadata['source']
                        page_content = doc.page_content
                        i = i + 1
                        with st.expander(f"**Источник N{i}:** [{source}]"):
                            st.write(page_content)

        if st.session_state['generated']:
            with response_container:
                for i in range(len(st.session_state['generated'])):
                    message(st.session_state["past"][i], is_user=True, key=str(
                        i) + '_user')
                    message(st.session_state["generated"][i], key=str(
                        i))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        # st.write(f"Что-то пошло не так. Возможно, не хватает входных данных для работы. {str(e)}")
        st.write(f"Не хватает входных данных для продолжения работы. См. панель слева.")