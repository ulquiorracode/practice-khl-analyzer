import fitz


def crop_and_shift_pdf(
    input_path: str,
    output_path: str,
    start_marker: str = "№ 9",
    end_marker: str = "№ 10",
) -> None:
    """Вырезает текст между маркерами и сдвигает его на самый верх страницы."""
    doc = fitz.open(input_path)
    out_doc = fitz.open()  # Создаем новый пустой документ

    page_start_idx = -1
    y_start = None
    page_end_idx = -1
    y_end = None

    # Шаг 1: Поиск координат маркеров в исходном документе
    for idx in range(len(doc)):
        page = doc[idx]

        # Ищем начало полезного текста
        if page_start_idx == -1:
            rects_start = page.search_for(start_marker)
            if rects_start:
                page_start_idx = idx
                y_start = rects_start[0].y0  # Верхняя граница "№9"

        # Ищем конец полезного текста
        rects_end = page.search_for(end_marker)
        if rects_end:
            page_end_idx = idx
            y_end = rects_end[0].y0  # Верхняя граница "№10"

    # Проверка на наличие маркеров
    if page_start_idx == -1 or page_end_idx == -1:
        print("Ошибка: Один или оба маркера не найдены в документе.")
        doc.close()
        out_doc.close()
        return

    if page_end_idx < page_start_idx or (
        page_end_idx == page_start_idx and y_end < y_start
    ):
        print(
            "Ошибка: Маркеры расположены некорректно (конец раньше начала)."
        )
        doc.close()
        out_doc.close()
        return

    # Шаг 2: Постраничный перенос полезных областей со сдвигом
    for idx in range(page_start_idx, page_end_idx + 1):
        src_page = doc[idx]
        width = src_page.rect.width
        height = src_page.rect.height

        # Создаем новую страницу стандартного размера в чистом документе
        new_page = out_doc.new_page(width=width, height=height)

        # Сценарий А: Весь текст уместился на одной странице
        if page_start_idx == page_end_idx:
            # Вырезаем область от y_start до y_end
            clip = fitz.Rect(0, y_start, width, y_end)
            # Размещаем ее на новой странице с самого верха (Y=0)
            dest = fitz.Rect(0, 0, width, y_end - y_start)
            new_page.show_pdf_page(dest, doc, idx, clip=clip)

        # Сценарий Б: Текст разбит на несколько страниц
        else:
            if idx == page_start_idx:
                # Первая страница: берем текст от y_start до самого низа листа
                clip = fitz.Rect(0, y_start, width, height)
                # Сдвигаем вверх на Y=0
                dest = fitz.Rect(0, 0, width, height - y_start)
                new_page.show_pdf_page(dest, doc, idx, clip=clip)

            elif idx == page_end_idx:
                # Последняя страница: берем текст от верха листа до координаты y_end
                clip = fitz.Rect(0, 0, width, y_end)
                # Размещаем без сдвига по вертикали (он и так вверху)
                dest = fitz.Rect(0, 0, width, y_end)
                new_page.show_pdf_page(dest, doc, idx, clip=clip)

            else:
                # Средние страницы переносим целиком без изменений
                new_page.show_pdf_page(src_page.rect, doc, idx)

    # Сохраняем очищенный документ
    out_doc.save(output_path, garbage=3, deflate=True)
    out_doc.close()
    doc.close()
    print(f"Документ успешно пересобран и сохранен в: {output_path}")


if __name__ == "__main__":
    crop_and_shift_pdf("задание.pdf", "задание2.pdf")
