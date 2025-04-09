import os
import requests


# ================ API Communication Functions ================
def _handle_remote_request(payload):
    """Lambda 함수에 API 요청을 보내고 응답을 처리하는 함수"""
    # Lambda function URL
    lambda_url = os.environ.get("LAMBDA_FUNCTION_URL")

    # Prepare headers
    headers = {"Content-Type": "application/json"}

    try:
        # Make the request to the Lambda function
        response = requests.post(
            lambda_url, headers=headers, json=payload, timeout=10  # Set a reasonable timeout
        )

        # Check if request was successful
        response.raise_for_status()
        print(response.json())

        return response.json()

    except requests.exceptions.RequestException as e:
        return None


# ================ Data Operations Functions ================
def upload_file(username, password, data, filename):
    """S3에 파일을 업로드하는 함수 - 인증 필요"""
    payload = {"username": username, "password": password, "data": data, "filename": filename}
    return _handle_remote_request(payload)


def delete_file(username, password, filename):
    """S3 파일을 삭제하는 함수 - 인증 필요"""
    payload = {"username": username, "password": password, "action": "delete_file", "filename": filename}
    return _handle_remote_request(payload)


# ================ Non-authenticated Access Functions ================
def list_macro_files():
    """macro_data 디렉토리의 파일 목록을 인증 없이 가져오는 함수"""
    payload = {"action": "list_all_files_no_auth"}
    return _handle_remote_request(payload)


def download_macro_file(owner, filename):
    """macro_data 디렉토리의 파일을 인증 없이 다운로드하는 함수"""
    payload = {"action": "download_file_no_auth", "owner": owner, "filename": filename}
    return _handle_remote_request(payload)


def download_skill_file():
    """skill_data 디렉토리의 파일을 인증 없이 다운로드하는 함수"""
    payload = {"action": "download_skill_file_no_auth"}
    return _handle_remote_request(payload)


# ================ Utility Functions ================
def get_sample_data():
    """샘플 매크로 데이터를 반환하는 함수"""
    return {
        "macroName": "Sample Macro",
        "description": "This is a sample macro data",
        "created": "2025-04-07T12:00:00Z",
        "steps": [
            {"id": 1, "action": "click", "target": "#button1"},
            {"id": 2, "action": "type", "target": "#input1", "value": "Hello World"},
        ],
    }


def main():
    # 작업 선택 메뉴 표시
    print("\n=== 작업 선택 ===")
    print("1. 매크로 파일 업로드 (로그인 필요)")
    print("2. 매크로 파일 목록 조회")
    print("3. 매크로 파일 다운로드")
    print("4. 매크로 파일 삭제 (로그인 필요)")
    print("5. skill_data 파일 다운로드")
    choice = input("작업을 선택하세요 (1-5): ").strip()

    username = os.environ.get("COGNITO_USERNAME")
    password = os.environ.get("COGNITO_PASSWORD")

    if choice == "1":
        # 파일 업로드 처리 (인증 필요)
        # 환경 변수에서 사용자 정보 가져오기

        filename = input("업로드할 파일 이름을 입력하세요: ").strip()
        if not filename:
            print("파일 이름이 필요합니다. 프로그램을 종료합니다.")
            return

        data = get_sample_data()
        result = upload_file(username, password, data, filename)

        if result:
            print("업로드 성공!")
        else:
            print("업로드 실패.")

    elif choice == "2":
        # 매크로 파일 목록 조회 (인증 필요 없음)
        print("\n매크로 파일 목록을 조회합니다...")
        result = list_macro_files()

        if result and "files" in result:
            files = result["files"]
            if files:
                print("\n=== 매크로 파일 목록 ===")
                for i, file_info in enumerate(files, 1):
                    filename = file_info.get("filename", "Unknown")
                    owner = file_info.get("owner", "Unknown")
                    created = file_info.get("created", "Unknown")
                    print(f"{i}. {owner}/{filename} (생성일: {created})")
            else:
                print("매크로 파일이 없습니다.")
        else:
            print("매크로 파일 목록 조회 실패")

    elif choice == "3":
        # 매크로 파일 다운로드 (인증 필요 없음)
        print("\n매크로 파일 목록을 조회합니다...")
        result = list_macro_files()

        if result and "files" in result:
            files = result["files"]
            if files:
                print("\n=== 매크로 파일 목록 ===")
                for i, file_info in enumerate(files, 1):
                    filename = file_info.get("filename", "Unknown")
                    owner = file_info.get("owner", "Unknown")
                    created = file_info.get("created", "Unknown")
                    print(f"{i}. {owner}/{filename} (생성일: {created})")

                # 다운로드할 파일 선택
                file_index = input("\n다운로드할 파일 번호를 입력하세요 (취소: 0): ")
                try:
                    file_index = int(file_index)
                    if file_index == 0:
                        print("파일 다운로드를 취소했습니다.")
                    elif 1 <= file_index <= len(files):
                        # 선택한 파일 다운로드
                        file_to_download = files[file_index - 1]["filename"]
                        owner = files[file_index - 1]["owner"]
                        print(f"{owner}/{file_to_download} 파일을 다운로드합니다...")
                        download_result = download_macro_file(owner, file_to_download)

                        print(download_result["data"])

                        if download_result:
                            print("다운로드 성공")
                        else:
                            print("다운로드 실패")
                    else:
                        print("잘못된 파일 번호입니다.")
                except ValueError:
                    print("숫자를 입력해주세요.")
            else:
                print("다운로드할 수 있는 매크로 파일이 없습니다.")
        else:
            print("매크로 파일 목록 조회 실패로 다운로드를 진행할 수 없습니다.")

    elif choice == "4":
        # 매크로 파일 삭제 (인증 필요)
        # 환경 변수에서 사용자 정보 가져오기

        print(f"\n{username}의 파일 목록을 조회합니다...")
        # 먼저 전체 파일 목록을 가져와서 해당 사용자의 파일만 필터링
        result = list_macro_files()

        if result and "files" in result:
            # 현재 사용자의 파일만 필터링
            user_files = [file for file in result.get("files", []) if file.get("owner") == username]

            if user_files:
                print("\n=== 내 파일 목록 ===")
                for i, file_info in enumerate(user_files, 1):
                    filename = file_info.get("filename", "Unknown")
                    created = file_info.get("created", "Unknown")
                    print(f"{i}. {filename} (생성일: {created})")

                # 삭제할 파일 선택
                file_index = input("\n삭제할 파일 번호를 입력하세요 (취소: 0): ")
                try:
                    file_index = int(file_index)
                    if file_index == 0:
                        print("파일 삭제를 취소했습니다.")
                    elif 1 <= file_index <= len(user_files):
                        # 선택한 파일 삭제
                        file_to_delete = user_files[file_index - 1]["filename"]
                        print(f"{file_to_delete} 파일을 삭제합니다...")
                        delete_result = delete_file(username, password, file_to_delete)

                        if delete_result:
                            print(f"파일 삭제 성공")
                        else:
                            print("파일 삭제 실패")
                    else:
                        print("잘못된 파일 번호입니다.")
                except ValueError:
                    print("숫자를 입력해주세요.")
            else:
                print(f"{username} 사용자의 파일이 없습니다.")
        else:
            print("파일 목록 조회 실패로 삭제를 진행할 수 없습니다.")

    elif choice == "5":
        # skill_data 파일 다운로드
        download_result = download_skill_file()

        if download_result:
            print("다운로드 성공")
        else:
            print("다운로드 실패")

    else:
        print("잘못된 선택입니다. 프로그램을 종료합니다.")


if __name__ == "__main__":
    main()
