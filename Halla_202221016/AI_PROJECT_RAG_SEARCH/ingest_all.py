from pathlib import Path
from src.rag_system import DocumentRAG
import time

print('문서 인덱싱을 시작합니다...\n')
start = time.time()
rag = DocumentRAG()
results = rag.ingest_folder()

ok_count = sum(1 for r in results if r.get('status') == 'ok')
empty_count = sum(1 for r in results if r.get('status') == 'empty')
skip_count = sum(1 for r in results if r.get('status') == 'skipped')

print('\n=== 인덱싱 완료 ===')
print('성공:', ok_count, '개')
print('빈 파일:', empty_count, '개')
print('제외됨:', skip_count, '개')

status = rag.get_status()
print('\n=== 학습 상태 ===')
print('찾은 문서:', status['supported_files_found'], '개')
print('인덱싱된 청크:', status['indexed_chunks'], '개')
print('소요 시간: {:.1f}초'.format(time.time() - start))
