from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
import logging

logger = logging.getLogger(__name__)

TRAINING_DATA = [
    ("I love this course so much, learned a lot!", "positive"),
    ("Great lecture today, the professor explained everything clearly", "positive"),
    ("Finally finished my project and it works perfectly!", "positive"),
    ("So excited for the upcoming hackathon on campus", "positive"),
    ("Amazing study group session, we nailed all the practice problems", "positive"),
    ("The campus library is beautiful and peaceful", "positive"),
    ("Got an A on my midterm, hard work pays off", "positive"),
    ("Really enjoying the Python course this semester", "positive"),
    ("Best semester so far, loving every class", "positive"),
    ("Our team project is going really well, super proud", "positive"),
    ("The new cafeteria food is actually really good", "positive"),
    ("Grateful for all the helpful professors at AUPP", "positive"),
    ("Just deployed my app successfully, feeling great", "positive"),
    ("The campus events are so fun and well organized", "positive"),
    ("Happy to be part of such a great university community", "positive"),
    ("Reminder: study group tonight at 7pm, library 4th floor", "neutral"),
    ("Does anyone know when the assignment is due?", "neutral"),
    ("The midterm covers chapters 1 through 6", "neutral"),
    ("Office hours are on Tuesday from 2 to 4pm", "neutral"),
    ("Looking for a group of 3 for the final project", "neutral"),
    ("The lecture was rescheduled to Thursday", "neutral"),
    ("Anyone selling their algorithms textbook?", "neutral"),
    ("New semester schedule has been posted on Canvas", "neutral"),
    ("The assignment instructions have been updated", "neutral"),
    ("Campus will be closed on Monday for the holiday", "neutral"),
    ("Registration for next semester opens next week", "neutral"),
    ("The final project is due at the end of week 8", "neutral"),
    ("Just submitted my proposal document", "neutral"),
    ("Looking for a Python tutor for extra help", "neutral"),
    ("The Wi-Fi in building B is a bit slow today", "neutral"),
    ("This assignment is so confusing, I have no idea what to do", "negative"),
    ("Failed my quiz today, so disappointed in myself", "negative"),
    ("The deadline was moved earlier with no notice, really frustrating", "negative"),
    ("I hate how stressful finals week is every semester", "negative"),
    ("The internet keeps cutting out during my online exam", "negative"),
    ("So tired and overwhelmed with all these assignments", "negative"),
    ("The professor never responds to emails, very unhelpful", "negative"),
    ("Wasted three hours debugging and still can't fix this error", "negative"),
    ("Group member is not contributing at all to the project", "negative"),
    ("This course is way too hard compared to what was advertised", "negative"),
    ("Really disappointed with the grading, seems unfair", "negative"),
    ("The classroom is too hot and it is hard to concentrate", "negative"),
    ("Missed the registration window, now I cannot enroll", "negative"),
    ("Feeling really burnt out this semester", "negative"),
    ("The parking situation on campus is terrible", "negative"),
]


class SentimentClassifier:
    def __init__(self):
        self.pipeline = None
        self._trained = False

    def train(self):
        texts  = [t for t, _ in TRAINING_DATA]
        labels = [l for _, l in TRAINING_DATA]
        X_train, X_val, y_train, y_val = train_test_split(
            texts, labels, test_size=0.2, random_state=42, stratify=labels
        )
        self.pipeline = Pipeline([
            ('tfidf', TfidfVectorizer(ngram_range=(1, 2), max_features=5000, stop_words='english')),
            ('clf',   LogisticRegression(max_iter=500, random_state=42, C=1.0)),
        ])
        self.pipeline.fit(X_train, y_train)
        self._trained = True
        y_pred = self.pipeline.predict(X_val)
        logger.info("Sentiment model trained.\n%s", classification_report(y_val, y_pred, zero_division=0))

    def predict(self, text: str) -> str:
        if not self._trained:
            self.train()
        return self.pipeline.predict([text])[0]


_classifier = SentimentClassifier()
_classifier.train()


def get_sentiment(text: str) -> str:
    return _classifier.predict(text)