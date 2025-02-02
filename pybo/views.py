from django.shortcuts import render

# Create your views here.
from rest_framework.decorators import api_view
from rest_framework.response import Response
import os
import pickle

import time
import google.generativeai as genai
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np

import textwrap

import environ
from config.settings import *
STATIC_ROOT = BASE_DIR / 'static/'

env = environ.Env()
environ.Env.read_env(BASE_DIR / '.env')

# Google API 키 설정
GOOGLE_API_KEY = env('API_KEY')
genai.configure(api_key=GOOGLE_API_KEY)

# Gemini 모델 초기화
model = genai.GenerativeModel('gemini-1.5-flash')

# 질문 임베딩 생성에 사용할 모델
embedding_model = SentenceTransformer('all-MiniLM-L6-v2') #


# 질문-답변 문서
qa_pairs = [
    #1. 불법촬영 기본 개념
    {"question": "불법촬영이란 무엇인가요?", "answer": "불법촬영이란 당사자의 동의를 받지 않은 채로 신체의 일부나 성적인 수치심 및 불쾌감을 유발할 수 있는 사진이나 영상을 촬영하는 것입니다. 지하철·화장실·탈의실 등 공공장소에 카메라를 설치하여 사적인 장면을 촬영하는 행위 등이 해당됩니다. 불법촬영으로 나온 매체를 ‘불법 촬영물’이라고 부릅니다."},
    {"question": "법촬영은 왜 문제가 되나요?", "answer": "불법촬영은 피해자의 개인정보와 프라이버시를 심각하게 침해하는 행위입니다. 또한, 불법 촬영물의 유포는 피해자에게 정신적 고통을 주며, 사회적으로도 범죄를 조장하는 문제가 됩니다."},
    {"question": "불법촬영의 법적 처벌은 어떻게 되나요?", "answer": "불법촬영은 형법과 정보통신망법, 성폭력처벌법 등 여러 법에 의해 처벌받을 수 있습니다. 처벌에는 징역형, 벌금형, 전자발찌 부착 등이 포함될 수 있으며, 피해자에 대한 손해배상도 이루어질 수 있습니다."},
    {"question": "몰래카메라와 불법촬영의 차이는 무엇인가요?", "answer": "몰래카메라는 명칭은 폭력과 호기심 어린 장난의 경계를 흐리고, 폭력을 가볍게 여겨지도록 만든다는 이유로 2017년 9월 청와대 국무회의에서 불법촬영으로 명칭이 공식 변경되었습니다."},
    #2. 불법촬영의 유형
    {"question": "불법촬영의 대표적인 유형은 무엇인가요?", "answer": "불법촬영의 유형으로는 촬영, 소지, 구입, 저장, 시청, 유포, 유포 협박, 합성이 있습니다. 각각의 뜻은 다음과 같습니다. \n 촬영 : 성적인 욕망 및 수치심을 일으키는 사진, 영상을 찍음 \n 소지 : 불법촬영물을 가지고 있음 \n 구입 : 촬영물을 돈을 주고 구입 \n 저장 : 촬영물을 내 스마트폰이나 컴퓨터에 저장 \n 시청 : 촬영물을 봄 \n 유포 : 촬영물을 퍼뜨림 \n 유포협박 : 촬영물 퍼뜨리겠다고 협박 \n 합성 : 성적인 수치심이 들게 편집"},
    {"question": "불법촬영을 위한 장비나 기기에는 어떤 것들이 있나요?", "answer": "스마트폰은 시간과 장소에 크게 구애받지 않고 범죄를 자행하기 위한 수단으로 사용되고 있는데 쉽게 고화질 스마트폰 카메라를 이용하여 상대방을 촬영할 수 있기 때문입니다."},
    {"question": "불법촬영 예시는 어떤 것이 있나요?", "answer": "학원에서 어떤 친구가 잘 모르는 다른 학교 친구의 얼굴을 몰래 촬영하는 것, 불법촬영물을 개인의 디지털 기기에 소지 및 저장하거나 구입하는 것, 불법촬영물을 재밋거리로 단톡방에 공유하는 것, 합성물을 단톡방이나 SNS에 올리는 것 등이 있습니다."},
    {"question": "불법촬영에 대한 심각성은 어느 정도 인가요?", "answer": "2017년도부터 2021년까지 불법촬영 범죄로 신고된 사건은 29,396건으로 집계되었으며, 2020년 행정안전부에서 발표한 카메라 등 이용촬영 범죄 건수는 서울에서만 총 16,523건으로 확인되었습니다. 카메라 이용촬영 범죄의 가해자와 피해자에 대한 통계현황을 보면 2020년 기준 범죄 가해자 수는 총 5,151명입니다."},
    #3. 불법촬영 피해 예방
    {"question": "불법촬영을 예방하기 위한 기본적인 방법은 무엇인가요?", "answer": "사진 촬영 시에는 상대방에게 동의를 구하여야 합니다. 동의는 다양한 방법으로 표현될 수 있는데 상대방이 적극적으로 좋다고 표현했을 때만 ‘yes’의 의미입니다. 특히 “좋다”고 말하지만 겁먹은 표정을 하거나 몸이 얼어붙거나 어깨를 으쓱하는 행동, 말을 돌리는 행동은 진정한 동의가 아닙니다."},
    {"question": "불법촬영 예방을 위해 개인이 할 수 있는 활동은 무엇이 있나요?", "answer": "불법촬영 예방을 위해 개인 차원에서 할 수 있는 것은 촬영 시 상호 합의하기, 인권, 인격 존중하기, 불법촬영 반대 운동에 참여하기, 공공장소에 불필요한 물건(예: 텀블러나 종이컵 같이 화장실에 있기에는 부적절한 물건이 있는 경우)이 있을 경우 확인하기, 이럴 경우 현장 보존을 위해 직접 만지지 말고 경찰에 신고하기 등이 있습니다."},
    {"question": "불법촬영 예방을 위해 사회가 할 수 있는 활동은 무엇이 있나요?", "answer": "사회와 국가 차원에서 할 수 있는 일은 화장실 등 불법촬영 가능성이 있는 곳을 수시로 점검하기, 불법촬영 예방 홍보 배너나 포스터, 스티커 붙이기, 처벌 강화, 수사과정에서 추가 피해(2차 가해)가 발생하지 않도록 주의하기, 웹하드 업체 감시와 제재 등이 있습니다."},
    {"question": "불법촬영 가해자가 되지 않으려면 어떻게 해야 하나요?", "answer": "불법촬영 가해자가 되지 않으려면 촬영 에티켓 지키기, 성역할 고정관념 버리기, 성인지 감수성 향상, 성충동 조절하기, 필요시 정서, 정신치료 받기 등이 있습니다."},
    {"question": "불법촬영 피해자가 되지 않으려면 어떻게 해야 하나요?", "answer": "다중이용시설(화장실, 탈의실 등)에서는 주의하여 살피기, 자신의 신체 사진을 보내달라는 채팅 거절하기, 불법촬영을 목격하거나 의심되면 경찰에 즉시 신고하기, 피해를 당한 경우 믿을 만한 어른께 말씀드리기, 불법촬영물이 유포되었다면 경찰에 신고하고 영상 삭제 지원 요청하기 등이 있습니다."},
    {"question": "타인의 권리를 존중하려면 어떻게 해야하나요?", "answer": "타인의 권리를 존중하기 위해 올바른 사진 촬영 문화에 대한 교육 받기, 사진을 찍을 때는 상대방의 동의를 구하기, 사진을 공유할 때 상대방의 허락을 받기, 사진을 공유하려고 할 때 배경에 모르는 사람이 찍혔다면 공유하지 않기, 반드시 공유해야 하는 경우에는 그 사람을 지우거나 모자이크 처리하기 등이 있습니다."},
    #4. 피해 발생 시 대응 방법
    {"question": "불법촬영 피해를 당했다면 어떻게 해야 하나요?", "answer": "1) 도움 요청: 불법촬영을 당했거나 불법촬영물을 목격한 경우 즉시 부모님이나 선생님 등 믿을 만한 어른에게 도움을 요청합니다. \n 2) 신고: 불법촬영을 경험하거나 불법촬영물을 목격한 경우 경찰 등 신고 체계를 활용하여 안전한 환경을 유지할 수 있도록 노력해야 합니다. \n 3) 책임감 있는 행동: 항상 자신의 행동에 책임을 져야 합니다. 다른 사람의 사생활을 존중하고, 촬영이나 녹음을 할 때는 그에 따른 책임을 인식하고 행동해야 합니다. 본인의 잘못을 알게 된 경우라면 사과하고 삭제하는 것에 최선을 다합니다."},
    {"question": "불법촬영 피해를 발견했을 때 신고 절차는 어떻게 되나요?", "answer": "경찰에 신고할 때는 불법촬영이 이루어진 장소, 시간, 방법 등을 정확히 기록하여 신고하는 것이 좋습니다. 전문가의 지원을 받아 증거를 확보할 수 있습니다."},
    {"question": "불법촬영 피해 시 어디에 신고할 수 있나요?", "answer": "사이버 경찰청 112, 방송통신심의위원회 1377, 여성긴급전화 1366, 디지털성범죄피해자지원센터 02-735-8994 등이 있습니다."},
    #5. 불법촬영과 관련된 법률
    {"question": "불법촬영과 관련된 주요 법률은 무엇인가요?", "answer": "개인정보 침해 및 촬영물 유포에 대한 처벌 규정으로 형법, 불법 촬영물의 유포 및 접근 제한에 따른 정보통신망법, 성폭력 처벌법 등이 있습니다."},
    {"question": "불법촬영에 대한 처벌은 어떤 방식으로 이루어지나요?", "answer": "불법촬영 유형에 따라 처벌이 달라집니다. 예를 들면 불법촬영은 7년 이하의 징역 또는 5천만원 이하의 벌금, 불법촬영물 반포 등은 3년 이상의 유기징역, 3년 이하의 징역 또는 3천만원 이하의 벌금, 불법촬영물 복제물을 소지, 구입, 저장 또는 시청한 자는 3년 이하의 징역 또는 3천만원 이하의 벌금 등이 있습니다."},
    #6. 불법촬영 피해자
    {"question": "불법촬영이 피해자에게 미치는 영향은 무엇인가요?", "answer": "불법촬영이 피해자에게 미치는 영향으로는 대인기피, 수치심, 유포에 대한 공포, 많은 사람들이 촬영물을 보았을 것에 대한 불안감, 우울, 삭제의 어려움 등이 있습니다."},
    {"question": "불법촬영 피해자를 위한 지원 기관은 어디인가요?", "answer": "대표적으로 다음과 같은 기관이 있습니다. \n 1) 디지털성범죄 피해자지원센터 (http://d4u.stop.or.kr) \n - 상담연락처: 02-735-8994 \n - 상담시간: (평일) 10:00~17:00 \n - 지원내용: 상담, 삭제지원, 수사지원 등 \n 2) 여성긴급전화(http://www.cyber-lion.com) \n - 상담연락처: 1366 \n - 상담시간: 365일 24시간 \n - 지원내용: 전문상담소, 각 지역경찰, 병원, 법률기관 등 연계 \n 3) 한국성폭력상담소(http://www.sisters.or.kr) \n - 상담연락처: 02-338-5801 \n - 상담시간: (평일) 10:00~17:00 \n - 지원내용: 성폭력 피해 생존자 상담 및 심리적, 의료적, 법률적 지원"},
    {"question": "피해자가 정신적 고통을 겪고 있다면 어떤 도움을 받을 수 있나요? & 피해자가 받을 수 있는 법적 지원은 무엇인가요?", "answer": "다음과 같은 지원을 받을 수 있습니다. \n 1) 피해자 상담, 삭제지원, 수사·법률·의료 연계, 심리·정서 지원 등으로 회복을 돕는다. \n 2) 전화 상담: 디지털 성범죄 피해자 지원센터는 365일 24시간 전화 상담을 제공하고 있다. \n 3) 온라인 상담: 디지털 성범죄 피해자 지원센터 홈페이지를 통해 온라인 상담을 신청할 수 있다. 온라인 상담은 언제 어디서나 편리하게 이용할 수 있다. \n 4) 방문 상담: 디지털 성범죄 피해자 지원센터는 전국에 지점을 운영하고 있다. 지점을 방문하여 상담 받을 수 있다. \n 5) 사회적 지원(의료 지원, 취업 지원, 가족 지원 등)"},
    #7. 불법촬영 예방을 위한 사회적 노력
    {"question": "불법촬영 예방을 위한 사회적 제도에는 무엇이 있나요?", "answer": "잠입 수사 및 신고포상금제 도입, 아동·청소년 대상 성범죄 신고포상금제도, 수요 차단 및 인식 개선, 디지털 성범죄 예방·대응방안을 공익광고 및 포털을 통해 홍보, 성범죄자 알림e 등이 있습니다."},
    {"question": "불법촬영 예방을 위한 기술적 노력에는 어떤 것들이 있나요?", "answer": "변형 카메라의 수입·판매업 등록제를 도입, 유통 이력 추적을 위한 이력 정보 시스템 데이터 베이스를 구축, IP 카메라 등 영상 촬영 기기에 대한 보안 강화, 이용자에게 초기 비밀번호 변경 등 IP 카메라 등 해킹 대응을 위한 인식 제고 홍보, IP 카메라 등 제조사에 단말기별 다른 비밀번호 설정 등 보안 조치를 강화하는 것 등이 있습니다."},
    #8. 불법촬영과 관련된 최신 이슈
    {"question": "최근 불법촬영 관련 사건은 어떤 것들이 있었나요?", "answer": "2018년 영남 및 충청권 숙박업소, 2020년 경남 김해고등학교 화장실, 2021년 버스 레깅스 촬영, 2022년 보건소 불법촬영 등이 있습니다. 위 사례 외에도 다양한 불법촬영 사건들이 발생하고 있으며, 피해 규모는 정확히 파악하기에는 한계가 있습니다. 그러나, 최근 몇 년 동안 불법촬영 신고 건수가 급증하고 있으며, 피해자 또한 증가하고 있습니다."},
    #9. 딥페이크 개념
    {"question": "딥페이크란 무엇인가요?", "answer": "딥페이크(Deepfake)는 인공지능 기술을 이용해 실제 사람의 얼굴이나 음성을 가짜로 만들어내는 기술입니다. 주로 영상에서 사람의 얼굴을 다른 사람의 얼굴로 바꾸거나, 실제 사람의 음성을 인공지능으로 합성하는 방식으로 사용됩니다."},
    {"question": "딥페이크와 일반적인 영상 편집의 차이점은 무엇인가요?", "answer": "딥페이크는 기존의 영상 편집 기술보다 훨씬 정교하고 사실적인 변환을 가능하게 합니다. 전통적인 편집은 주로 이미지나 영상을 물리적으로 자르고 붙이는 방식으로 작업하지만 딥페이크는 AI를 이용해 사람의 얼굴, 표정, 음성 등을 매우 자연스럽게 변형할 수 있습니다."},
    {"question": "딥페이크는 불법인가요?", "answer": "딥페이크 자체가 불법이 아닙니다. 하지만 이를 불법적으로 활용하는 것은 범죄에 해당합니다. 예를 들어, 타인의 얼굴을 무단으로 합성해 명예훼손, 성적 착취 영상, 허위 정보 유포 등에 사용하면 법적으로 처벌을 받을 수 있습니다. 각국에서는 딥페이크 기술 악용에 대한 법적 규제를 강화하고 있습니다."},
    {"question": "친구들끼리 딥페이크로 놀아도 불법인가요?", "answer": "친구들끼리 딥페이크를 사용해 놀 때에도 상대방의 동의를 받지 않으면 초상권 침해나 개인정보 보호법 위반이 될 수 있습니다. 특히 성적 내용이나 모욕적 영상은 법적 처벌을 받을 수 있습니다. 따라서 타인의 이미지나 영상을 사용할 때는 반드시 동의를 얻고 윤리적인 범위 내에서 사용하는 것이 중요합니다."},
    {"question": "불법촬영과 딥페이크는 어떻게 연관될 수 있나요?", "answer": "딥페이크 기술은 불법촬영된 영상을 기반으로 사람의 얼굴을 합성하여 가짜 성적 영상을 만들어낼 수 있습니다. 예를 들어 불법촬영된 영상에 피해자의 얼굴을 합성하거나 유명인의 얼굴을 불법적으로 사용하여 성적 착취 영상을 만들거나 유포하는 방식으로 악용될 수 있습니다."},
    {"question": "청소년 중 딥페이크 이용자가 증가하는 이유가 무엇인가요?", "answer": "청소년들은 소셜미디어(SNS)와 애플리케이션(앱) 등을 통해 딥페이크 기술을 쉽게 익힐 수 있고, 제작 의뢰도 어렵지 않습니다. 문제는 이를 자주 접하면서 딥페이크 음란물이 피해자에게 큰 타격을 입히는 범죄라는 인식이 옅어질 수 있다는 점입니다."},
    #10. 딥페이크 유형
    {"question": "딥페이크는 어떤 문제를 일으킬 수 있나요?", "answer": "딥페이크 기술은 악용될 경우 사람의 얼굴, 목소리, 행동 등을 조작하여 가짜 영상을 만들어 낼 수 있습니다. 유명인의 명예를 훼손하거나, 가짜 뉴스, 성적 착취 영상, 정치적 선전 등의 불법적인 목적에 사용될 수 있습니다."},
    {"question": "딥페이크 악용의 유형은 무엇인가요?", "answer": "성적 착취 영상: 딥페이크 기술을 이용해 유명인이나 일반인의 얼굴을 합성하여 성적인 영상을 만들어 유포하는 사례가 많습니다. \n 정치적 악용: 정치인이나 공공 인물의 말을 왜곡하거나 허위 정보를 담은 가짜 영상을 만들어 여론을 조작하는 데 사용될 수 있습니다. \n 명예훼손: 딥페이크를 이용해 특정 인물의 명예를 훼손하거나 거짓된 이미지로 대중에게 전달하여 그들의 신뢰를 떨어뜨릴 수 있습니다."},
    {"question": "딥페이크 악용 심각성은 어느정도 인가요?", "answer": "‘딥페이크 범죄 현황’에 따르면 허위 영상물 관련 범죄는 2021년 156건에서 2022년 160건, 2023년 180건으로 증가세입니다. 2023년 기준 허위 영상물 범죄 피의자 120명 중 10대는 91명(75.8%)으로 4명 중 3명꼴이었습니다. 이어 20대는 24명(20.0%), 30대 4명(3.3%), 60대 1명(0.8%) 순입니다."},
    {"question": "딥페이크는 어떻게 악용되고 있나요?", "answer": "딥페이크 기술은 신종 학폭(학교폭력) 등으로도 악용되고 있습니다. 부산시교육청과 경찰 등에 따르면 부산의 한 중학교 학생 4명은 인공지능(AI)으로 같은 학교 학생 등 18명 등의 얼굴과 음란 사진을 합성한 80여장을 만들어 공유했습니다."},
    #11. 딥페이크 예방
    {"question": "딥페이크 피해를 예방하려면 어떻게 해야 하나요?", "answer": "딥페이크의 피해를 예방하려면 정보의 출처를 확인하는 습관을 기르는 것이 중요합니다. 영상이나 사진을 믿기 전에 그것이 진짜인지 확인할 수 있는 방법을 사용하고, 의심스러운 콘텐츠는 신뢰할 수 있는 매체나 전문가에게 확인하는 것이 필요합니다."},
    {"question": "딥페이크 피해를 당했다면 어떻게 해야 하나요?", "answer": "딥페이크 피해를 당한 경우 즉시 해당 영상을 삭제하고 법적 대응을 준비해야 합니다. 피해를 입은 사람은 경찰에 신고하거나, 법적 절차를 통해 해당 영상을 차단하고 명예훼손 등에 대해 민사소송을 제기할 수 있습니다."},
    {"question": "딥페이크가 유포될 때 어떻게 대응할 수 있나요?", "answer": "딥페이크가 유포된 경우 즉시 해당 플랫폼에 신고하여 삭제를 요청하고 관련 기관에 신고해야 합니다. 법적 대응을 통해 가짜 영상이 더 이상 유포되지 않도록 막을 수 있습니다."},
    {"question": "악용된 딥페이크 영상물을 발견했다면 어떻게 대처할 수 있나요?", "answer": "악용된 딥페이크 영상을 발견하면 해당 영상이 유포된 플랫폼에 즉시 신고하고 삭제 요청을 해야 합니다. 경찰에 신고하여 수사를 요청하고 법적 대응을 위해 변호사와 상담할 수 있습니다. 피해자는 민사소송을 통해 손해배상을 청구할 수 있습니다. 빠르게 대응하는 것이 중요합니다."},
    #12. 딥페이크 법률
    {"question": "딥페이크로 불법촬영 영상을 만들어 유포하는 것은 어떤 법적 처벌을 받나요?", "answer": "'성폭력범죄의 처벌 등에 관한 특례법'이나 '정보통신망 이용촉진 및 정보보호 등에 관한 법률'에 의해 강력히 처벌됩니다. 이러한 행위는 성적 착취, 명예훼손, 개인정보 침해 등의 범죄로 형사처벌을 받을 수 있으며 피해자는 민사소송을 통해 손해배상도 청구할 수 있습니다."},
    {"question": "딥페이크 기술에 대한 규제는 어떻게 이루어지고 있나요?", "answer": "각국에서는 딥페이크 기술에 대한 규제를 강화하기 위해 관련 법률을 제정하고 있습니다. 예를 들어, 미국에서는 딥페이크를 악용하는 사람들에게 징역형을 부과하는 법안을 논의 중이며, 유럽연합은 인공지능 기술과 관련된 규제를 강화하고 있습니다. 한국은 성적 착취 영상을 딥페이크로 만드는 것에 대한 처벌을 강화하는 법안을 제정한 바 있습니다."},
    {"question": "불법촬영과 딥페이크의 피해자가 될 가능성을 줄이려면 어떻게 해야 하나요?", "answer": "불법촬영과 딥페이크 피해를 예방하기 위해서는 온라인 및 오프라인에서 개인의 사생활을 철저히 보호하고, 영상이나 이미지를 무단으로 사용하지 않도록 주의해야 합니다. 또한, 딥페이크를 탐지하는 기술이나 서비스를 활용하여 자신을 보호할 수 있으며, 의심스러운 콘텐츠에 대해 경각심을 가지는 것이 중요합니다."},
    {"question": "딥페이크 기술을 악용하지 않으려면 어떻게 해야 하나요?", "answer": "딥페이크 기술을 악용하지 않으려면 먼저 기술의 윤리적 사용에 대한 충분한 인식이 필요합니다. 딥페이크 기술을 긍정적인 목적에만 사용하고 타인의 얼굴이나 목소리를 합성할 때는 반드시 동의를 받아야 하며 이를 상업적이나 악의적인 목적에 사용하지 않아야 합니다."},

]

# 캐시 파일 경로
CACHE_FILE = "embedding_cache.pkl"

# 임베딩 캐싱 함수
def cache_embeddings(questions):
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, 'rb') as f:
            cache = pickle.load(f)
    else:
        cache = {}

    # 새로운 질문 임베딩 계산
    new_embeddings = []
    for question in questions:
        if question not in cache:
            embedding = embedding_model.encode([question])
            cache[question] = embedding
        new_embeddings.append(cache[question])

    # 캐시 저장
    with open(CACHE_FILE, 'wb') as f:
        pickle.dump(cache, f)

    return np.vstack(new_embeddings)


# 1. 문서 질문 임베딩 생성
questions = [pair["question"] for pair in qa_pairs]
answers = [pair["answer"] for pair in qa_pairs]
question_embeddings = cache_embeddings(questions)

# 2. FAISS로 질문 임베딩 인덱싱
dimension = question_embeddings.shape[1]
index = faiss.IndexFlatL2(dimension)
index.add(np.array(question_embeddings))

# 3. 사용자 질문 입력 및 유사도 계산
def find_most_similar_question(user_question):
    # 사용자 질문 임베딩 생성
    user_embedding = embedding_model.encode([user_question])
    # 가장 유사한 질문 찾기
    distances, indices = index.search(user_embedding, k=1)
    most_similar_idx = indices[0][0]
    similarity_score = distances[0][0]
    return questions[most_similar_idx], answers[most_similar_idx], similarity_score
# 4. Gemini API와 연동하여 답변 생성
def get_gemini_response(user_question, context_question, context_answer):
    prompt = f"""
    The user has asked the following question:
    "{user_question}"

    The most similar question from the document is:
    "{context_question}"

    The corresponding answer from the document is:
    "{context_answer}"

    Based on this information, generate a detailed and user-friendly answer.
    """
    response = model.generate_content(
        prompt,
        generation_config=genai.types.GenerationConfig(
            candidate_count=1,
            temperature=0.7
        )
    )
    return response.candidates[0].content.parts[0].text


@api_view(['POST'])
def test_api(request):
    user_question = request.data.get('prompt')
    start_time = time.time()
    print(f"사용자 질문 : {user_question}")
    # 유사한 질문 검색
    context_question, context_answer, score = find_most_similar_question(user_question)
    print(f"\n가장 유사한 질문: {context_question}")
    print(f"\n해당 답변: {context_answer}")
    print(f"\n유사도 점수: {score:.8f}")

    # Gemini API로 답변 생성
    detailed_response = get_gemini_response(user_question, context_question, context_answer)

    formatted_response = "\n\n".join(
        textwrap.fill(para.strip(), width=60) for para in detailed_response.strip().split("\n\n")
    )

    print("\nGemini의 응답:")
    print(formatted_response)

    end_time = time.time()
    execution_time = end_time - start_time

    print(f"\n실행 시간: {execution_time:.2f} 초")
    rtr =[str(context_question), str(context_answer), str(score), str(formatted_response), str(execution_time)]
    print(rtr)
    return Response(rtr)





