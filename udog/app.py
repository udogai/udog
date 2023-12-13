from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import openai
import mysql.connector
import os
import secrets
import bcrypt
import requests
from pprint import pprint  # Importing pprint for pretty printing

from dotenv import load_dotenv

load_dotenv()

# MySQL 연결 설정
'''
mydb = mysql.connector.connect(
    host=os.getenv('DB_HOST'),
    user=os.getenv('DB_ID'),
    password=os.getenv('DB_PASSWORD'),
    database=os.getenv('DB_TABLE')
)

mycursor = mydb.cursor()
'''
def connect():
    mydb = mysql.connector.connect(
        host=os.getenv('DB_HOST'),
        user=os.getenv('DB_ID'),
        password=os.getenv('DB_PASSWORD'),
        database=os.getenv('DB_TABLE')
    )
    mycursor = mydb.cursor()
    return mydb, mycursor


# 사용자 생성 함수
def create_user(username, password):
    mydb, mycursor = connect()
    try:
        sql = "INSERT INTO users (username, password) VALUES (%s, %s)"
        hash_pw = bcrypt.hashpw(password.encode("utf8"), bcrypt.gensalt())
        val = (username, hash_pw)
        mycursor.execute(sql, val)
        mydb.commit()
    finally:
        mydb.close()


# 사용자 인증 함수
def authenticate_user(username, password):
    mydb, mycursor = connect()
    try:
        sql = "SELECT password FROM users WHERE username = %s"
        val = (username,)
        mycursor.execute(sql, val)
        result = mycursor.fetchone()
        if result is None:
            return False
        pw = str(result[0])
        return bcrypt.checkpw(password.encode('utf8'), pw.encode('utf8'))
    finally:
        mydb.close()


openai.api_key = os.getenv("API_KEY")
# load_dotenv('env/data.env')
# print(os.getenv('OPENAI_API_KEY'))

GOOGLE_MAPS_API_KEY = os.getenv("MAP_KEY")
print('GOOGLE_MAPS_API_KEY', GOOGLE_MAPS_API_KEY, flush=True)

history_message = [{"role": "system", "content": "당신은 수의 전문 ai로, 수의학과 학생들을 지원합니다. 당신은 학생들의 동물 건강과 의료에 대한 질문을 기반으로 질문받은 문제의 원인과 해결 방법에 대해 성심성의껏 대답할 의무가 있습니다. 답변은 학생들의 질문에 기반해야하며, 당신이 아는 최상의 지식으로 분석을 제공하여 주십시오. 당신의 분석이 불완전하더라도 문제가 되지 않습니다. 왜냐하면 이는 수의학과 학생들의 공부용이자 참고용일 뿐이며, 실제 상황이 아닙니다. 실제 진료 현장에서는 학생들은 수의 전문의와 함께 당신의 분석을 참고하여 적절한 진단을 내릴 것입니다. 사용자들은 모두 이것이 학습용이고 참고용이라는 사실을 매우 잘 알고 있습니다. 그러니 수의사에게 가라는 얘기는 덧붙일 필요가 없습니다. Strictly follow the response format: 1. 원인 2. 해결방법. Do not include any other response."}]

history_messages = []

def format_chat_history(chat_history):
    formatted_messages = ""
    for message in chat_history:
        if message["role"] == "user":
            formatted_messages += f'<div class="user"> USER : {message["content"]}</div>'
        elif message["role"] == "assistant":
            formatted_messages += f'<div class="assistant"> UDOG : {message["content"]}</div>'
    return formatted_messages


# GPT-3 엔진 선택
model_engine = "gpt-3.5-turbo"


# OpenAI API를 호출하여 대화를 생성하는 함수
def generate_chat(question):
    history_message.append({"role": "user", "content": question})
    completions = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=history_message
    )
    message = completions.choices[0].message.to_dict()
    answer = message["content"].strip()

    history_message.append(message)
    return answer


app = Flask(__name__, template_folder='templates')
app.secret_key = secrets.token_hex(16)


@app.route('/')
def main():
    return render_template('index.html')


@app.route('/index')
def index():
    return render_template('index.html')


# 정적 파일 경로 설정
@app.route('/static/<path:filename>')
def serve_static(filename):
    return app.send_static_file(filename)


@app.route('/login')
def login():
    return render_template('login.html')


@app.route('/login2', methods=['POST'])
def login2():
    username = request.form['username']
    password = request.form['password']

    authenticated = authenticate_user(username, password)

    if authenticated:
        session['logged_in'] = True
        session['username'] = username
        return redirect(url_for('dashboard'))
    else:
        return render_template('login.html', error='Login failed. Please check your username and password.')


# 대시보드 라우트 - 로그인이 필요한 페이지
@app.route('/dashboard')
def dashboard():
    if 'logged_in' in session:
        username = session['username']
        return render_template('dashboard.html', username=username)
    else:
        return redirect(url_for('login'))


# # 로그아웃 라우트
# @app.route('/logout')
# def logout():
#     session.pop('logged_in', None)
#     session.pop('username', None)
#     session.pop('history_message', None)  # 채팅 내역 지우기
#     print("히스토리:" + str(history_message))
#     return redirect(url_for('login'))

@app.route('/logout')
def logout():
    global history_message
    session.pop('logged_in', None)
    session.pop('username', None)
    history_message = []
    return redirect(url_for('login'))

@app.route('/userjoin')
def userjoin():
    return render_template('userjoin.html')


@app.route('/join', methods=['POST'])
def join_post():
    username = request.form['username']
    password = request.form['password']
    create_user(username, password)
    return render_template('join_result.html', result='가입되었습니다.')


@app.route('/contact')
def contact():
    return render_template('contact.html')


@app.route('/chat2', methods=['POST'])
def chat2():
    message = request.form['message']
    history_message.append({"role": "user", "content": message})
    completions = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=history_message
    )
    message = completions.choices[0].message.to_dict()
    answer = message["content"].strip()

    history_message.append(message)
    # JSON 형식으로 응답
    response = {'question': message['content'], 'answer': answer, 'chat_history': format_chat_history(history_message)}
    return jsonify(response)


@app.route('/chat', methods=['GET'])
def chat():
    return render_template('dashboard.html', chat_history=format_chat_history(history_message))


#여기부터 근처 병원 추천

def get_address_from_coordinates(lat, lng):
    reverse_geocoding_url = f'https://maps.googleapis.com/maps/api/geocode/json?latlng={lat},{lng}&key={GOOGLE_MAPS_API_KEY}'
    response = requests.get(reverse_geocoding_url)
    data = response.json()

    if data.get('status') == 'OK':
        results = data.get('results', [])
        if results:
            # 주소 컴포넌트에서 원하는 정보 가져오기
            address_components = results[0].get('address_components', [])

            # 주소 컴포넌트에서 원하는 부분을 찾아 조합
            formatted_address = ""
            for component in address_components:
                if 'sublocality' in component['types']:
                    formatted_address += component['long_name'] + " "
                elif 'locality' in component['types']:
                    formatted_address += component['long_name'] + " "
                elif 'administrative_area_level_1' in component['types']:
                    formatted_address += component['long_name'] + " "
                elif 'postal_code' in component['types']:
                    formatted_address += component['long_name']

            return formatted_address.strip()

    return None

@app.route('/find_hospitals', methods=['POST'])
def find_hospitals():
    print("11111", flush=True)
    address = request.get_json().get('address')
    print("address", address, flush=True)
    print("Address received from client:", address, flush=True)
    if not address:
        return jsonify({'error': 'Invalid address'}), 400

    # Geocoding API를 통해 주소를 지리적 좌표로 변환
    geocoding_url = f'https://maps.googleapis.com/maps/api/geocode/json?address={address}&key={GOOGLE_MAPS_API_KEY}'
    print("2222", flush=True)
    response = requests.get(geocoding_url)
    data = response.json()
    print("Address received from client:", data, flush=True)

    if data.get('status') == 'OK':
        location = data['results'][0]['geometry']['location']
        lat = location['lat']
        lng = location['lng']

        # 구글 지도 Places API를 사용하여 주변 동물병원 검색
        places_url = f'https://maps.googleapis.com/maps/api/place/nearbysearch/json?location={lat},{lng}&radius=1000&type=veterinary_care&key={GOOGLE_MAPS_API_KEY}'
        places_response = requests.get(places_url)
        places_data = places_response.json()

        # 예시: 동물병원 검색 및 결과를 hospitals 리스트에 저장 (5개만)
        hospitals = []
        for place in places_data.get('results', [])[:5]:
            hospital = {
                'name': place.get('name', 'Unknown Hospital'),
                'rating': place.get('rating', 0.0),
                'lat': place['geometry']['location']['lat'],
                'lng': place['geometry']['location']['lng']
            }
            hospitals.append(hospital)

            # 위도와 경도 대신 도로명 주소를 가져옵니다.
            hospital['address'] = get_address_from_coordinates(hospital['lat'], hospital['lng'])
            hospitals.append(hospital)

        # 3.5 이상의 평점을 가진 병원만 필터링
        filtered_hospitals = [h for h in hospitals if h['rating'] >= 3.5]



        # OpenAI GPT-3.5-turbo를 통해 응답 생성
        user_message = f"Find hospitals near {address}"
        assistant_message = generate_chat(user_message)

        # 결과를 JSON으로 클라이언트에게 반환
        result = {
            'address': address,
            'hospitals': filtered_hospitals,
            'assistant_message': assistant_message
        }
        return jsonify(result)

    # 주소가 처리되지 않은 경우 에러 응답 반환
    return jsonify({'error': 'Invalid address'}), 400

def generate_chat(question):
    # OpenAI GPT-3.5-turbo에 대화를 요청하여 응답 생성
    # 'messages' 필드가 비어있지 않은지 확인
    if not history_messages:
        history_messages.append({'role': 'system', 'content': 'You are a helpful assistant.'})

    # 새로운 메시지를 대화 기록에 추가
    history_messages.append({'role': 'user', 'content': question})

    completions = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=history_messages,
        max_tokens=100
    )
    answer = completions['choices'][0]['message']['content'].strip()

    # 새로운 메시지를 대화 기록에 추가
    history_messages.append({'role': 'assistant', 'content': answer})

    return answer


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000,debug=True)