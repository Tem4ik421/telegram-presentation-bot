# test_generate.py
import importlib.util
spec = importlib.util.spec_from_file_location('bot_main', 'main.py')
bot_main = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bot_main)

blocks = [
    {'title': 'Название презентации (титул)', 'body': 'Создано тестом'},
    {'title': 'Слайд 1', 'body': 'Первый абзац\n- Пункт A\n- Пункт B\nВторой абзац'},
    {'title': 'Слайд 2', 'body': '* Марк1\n* Марк2\nДополнительный текст'}
]

fname = bot_main.create_pdf_from_blocks(blocks, 'localtest')
print('Создан файл:', fname)