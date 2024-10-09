<ol>
  <li>Склонировать проект</li>
  <li>Создать виртуальное окружение `python -m venv myenv`</li>
  <li>Активировать виртуальное окружение `myenv\Scripts\activate`</li>
  <li>Установить библиотеки из requirements.txt `pip install requirements.txt`</li>
  <li>Добавить .env файл в корневую папку</li>
  <li>Применить миграции `alembic upgrade head`</li>
  <li>Перейти в подкаталог `cd src`</li>
  <li>Запустить сервер командой `uvicorn main:app --reload`</li>
</ol>
<b>docs: 127.0.0.1:8000/docs</b>
