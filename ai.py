import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
import random

class AIModel
    def __init__(self, model_name str)
        self.model_name = model_name
        self.model = None
        self.tokenizer = None
        self.loaded = False
        self._load_model()
    
    def _load_model(self)
        Загружает модель в фоне
        try
            print(f📥 Загрузка модели {self.model_name}...)
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            if self.tokenizer.pad_token is None
                self.tokenizer.pad_token = self.tokenizer.eos_token
            
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                torch_dtype=torch.float32,
                low_cpu_mem_usage=True
            )
            self.loaded = True
            print(f✅ Модель {self.model_name} загружена!)
        except Exception as e
            print(f❌ Ошибка загрузки модели {e})
            self.loaded = False
    
    def generate_response(self, user_message str, mode str = family) - str
        Генерирует ответ на сообщение
        if not self.loaded
            return ⏳ Модель еще загружается. Подождите немного!
        
        try
            # Контекст в зависимости от режима
            mode_styles = {
                family Ты заботливый семейный помощник. Отвечай тепло и с любовью. 💕,
                funny Ты веселый и остроумный друг. Шути и поднимай настроение! 🤪,
                strict Ты деловой ассистент. Отвечай четко и по делу. 📌,
                child Ты дружелюбный игровой помощник. Говори просто и весело! 🌈
            }
            
            style = mode_styles.get(mode, mode_styles[family])
            prompt = f{style}nПользователь {user_message}nАссистент
            
            inputs = self.tokenizer.encode(
                prompt,
                return_tensors=pt,
                truncation=True,
                max_length=256
            )
            
            with torch.no_grad()
                outputs = self.model.generate(
                    inputs,
                    max_length=200,
                    num_return_sequences=1,
                    temperature=0.9,
                    top_p=0.95,
                    do_sample=True,
                    pad_token_id=self.tokenizer.eos_token_id,
                    repetition_penalty=1.2
                )
            
            full_response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            if Ассистент in full_response
                response = full_response.split(Ассистент)[-1].strip()
            else
                response = full_response.replace(prompt, ).strip()
            
            if len(response)  2
                response = random.choice([
                    Интересно... расскажи еще! 🤔,
                    Я тебя слушаю! 👂,
                    Здорово! А что дальше 😊
                ])
            
            return response
        except Exception as e
            print(fОшибка генерации {e})
            return 😅 Ой, я что-то задумался. Давай еще раз

# Комплименты, шутки и загадки (если модель не готова)
COMPLIMENTS = [
    Ты сегодня просто сияешь! ✨,
    У тебя прекрасная улыбка! 😊,
    Ты самый замечательный человек! 💖,
    Я тобой восхищаюсь! 🌟,
    Ты делаешь этот мир лучше! 🌍,
]

JOKES = [
    Почему коты не играют в покер 🐱 Потому что они всегда блефуют!,
    Что говорит корова, когда хочет пошутить 🐄 Му-ха-ха!,
    Почему рыбы не играют на пианино 🐟 Потому что они боятся клавиш!,
]

RIDDLES = [
    {question Зимой и летом одним цветом 🎄, answer елка},
    {question Что можно увидеть с закрытыми глазами 😴, answer сон},
    {question Кто говорит на всех языках 🗣️, answer эхо},
]

def get_compliment()
    return random.choice(COMPLIMENTS)

def get_joke()
    return random.choice(JOKES)

def get_riddle()
    riddle = random.choice(RIDDLES)
    return riddle[question], riddle[answer]