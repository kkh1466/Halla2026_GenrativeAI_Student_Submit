# 문서 넣는 위치

이 프로젝트는 기본적으로 `data/documents/` 아래의 문서를 RAG 검색용 벡터 DB에 자동 반영합니다.

- 문서를 `data/documents/` 또는 그 하위 폴더에 넣으면 됩니다.
- 지원 형식: `.pdf`, `.xlsx`, `.xls`, `.doc`, `.docx`, `.hwp`, `.hwpx`, `.pptx`, `.ppt`, `.txt`, `.md`, `.csv`
- 같은 파일을 수정해서 다시 저장해도 파일 크기/수정 시간이 바뀌면 자동으로 다시 인덱싱합니다.
- 서버 실행 중에는 약 5초마다 새 파일과 변경된 파일을 확인합니다.

## 수동 업데이트

자동 반영을 기다리지 않고 바로 업데이트하려면 서버 실행 후 아래 API를 호출합니다.

```text
POST http://localhost:8000/ingest
```

## 학습률 확인

여기서 말하는 학습률은 모델 재훈련률이 아니라, 현재 문서 인덱싱 진행률입니다.

```text
GET http://localhost:8000/learning-status
GET http://localhost:8000/status
```

응답의 `percent` 또는 `learning_rate`가 현재 반영 진행률입니다.
