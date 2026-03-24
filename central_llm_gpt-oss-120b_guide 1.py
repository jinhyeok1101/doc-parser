"""
=======================================================================
 LiteLLM Central LLM 서비스 사용 가이드
=======================================================================

이 스크립트는 사내 Central LLM 서비스(LiteLLM Proxy)를 OpenAI Python SDK로
호출하는 기본 예제입니다. 아래 순서대로 동작합니다:

  1. LiteLLM Proxy에 연결하여 사용 가능한 모델 목록을 조회합니다.
  2. 스트리밍(streaming) 방식으로 채팅 요청을 보냅니다.
  3. 첫 토큰이 도착하는 데 걸린 시간(TTFT, Time To First Token)을 측정합니다.

-----------------------------------------------------------------------
 사전 준비 (Prerequisites)
-----------------------------------------------------------------------
  pip install openai

-----------------------------------------------------------------------
 설정 (Configuration)
-----------------------------------------------------------------------
  API 키와 Proxy URL은 아래 상수(API_KEY, BASE_URL)를 수정하세요.
  보안을 위해 실제 서비스에서는 환경 변수나 .env 파일로 관리하는 것을 권장합니다.

    예시:
      import os
      API_KEY = os.getenv("CENTRAL_LLM_API_KEY")

=======================================================================
"""

import time
from openai import OpenAI

# ---------------------------------------------------------------------------
#  설정값 (Configuration)
# ---------------------------------------------------------------------------

API_KEY  = "sk-9XBzzMCXKca7bjjrcMgqnA"   # LiteLLM Proxy에서 발급받은 API 키
BASE_URL = (                               # LiteLLM Proxy 서버 주소
    "https://doogpu.doosan.com/standard/workspace/"
    "ws-94c8469a-43a7-4573-a455-2926fa446865/"
    "workload/wl-e505ede6-881f-4185-983e-a13fb0d3f202/reserved2"
)
MODEL    = "gpt-oss-120b"                 # 사용할 모델명 (Proxy에 등록된 이름)

# ---------------------------------------------------------------------------
#  클라이언트 초기화 (Client Initialization): OpenAI SDK의 base_url을 LiteLLM Proxy 주소로 변경하여 OpenAI 코드 그대로 사내 LLM을 사용할 수 있습니다.
# ---------------------------------------------------------------------------

client = OpenAI(
    api_key=API_KEY,
    base_url=BASE_URL,
)

# ---------------------------------------------------------------------------
#  (선택) 사용 가능한 모델 목록 조회
# ---------------------------------------------------------------------------
print("=" * 60)
print("사용 가능한 모델 목록:")

try:
    models = client.models.list()
    for m in models.data:
        print(f"  - {m.id}")
except Exception as e:
    print(f"  모델 목록 조회 실패: {e}")

print("=" * 60)

# ---------------------------------------------------------------------------
#  스트리밍 채팅 요청 (Streaming Chat)
# ---------------------------------------------------------------------------
# stream=True 로 설정하면 응답이 토큰 단위로 즉시 전달됩니다.

MESSAGES = [
    {"role": "system",  "content": "You are a helpful assistant."},
    {"role": "user",    "content": "AI에 대해서 설명해줘"},
]

print(f"\n🤖 [{MODEL}] 답변:\n")

start_time = time.time()  # 요청 전송 시각

response = client.chat.completions.create(
    model=MODEL,
    messages=MESSAGES,
    stream=True,
)

# 스트림 응답 처리
first_token_received = False
ttft = 0.0

for chunk in response:
    delta_content = chunk.choices[0].delta.content

    # 첫 번째 토큰 도착 시점 기록
    if not first_token_received and delta_content is not None:
        ttft = time.time() - start_time
        first_token_received = True

    if delta_content is not None:
        print(delta_content, end="", flush=True)

# ---------------------------------------------------------------------------
#  (선택) TTFT 측정
# ---------------------------------------------------------------------------

print(f"\n\n⏱️  TTFT (Time To First Token): {ttft:.4f} 초")
print("✅ 스트리밍 완료")
