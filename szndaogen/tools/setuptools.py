def get_file_content_as_list(file_path: str) -> list:
    with open(file_path, "r", encoding="utf-8") as file:
        content = [line.strip() for line in file]
    return content


def get_file_content(file_path: str) -> str:
    with open(file_path, "r", encoding="utf-8") as file:
        content = file.read()
    return content
