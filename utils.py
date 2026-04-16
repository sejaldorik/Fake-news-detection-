import pickle
import re
import string
import pdfplumber
from newspaper import Article
from lime.lime_text import LimeTextExplainer

class MLEngine:
    def __init__(self, model_path='model.pkl', vectorizer_path='vectorizer.pkl'):
        try:
            with open(model_path, 'rb') as f:
                self.model = pickle.load(f)
            with open(vectorizer_path, 'rb') as f:
                self.vectorizer = pickle.load(f)
            self.explainer = LimeTextExplainer(class_names=['True', 'Fake'])
            self.is_loaded = True
        except FileNotFoundError:
            self.is_loaded = False
            self.model = None
            self.vectorizer = None
            
    def clean_text(self, text):
        text = text.lower()
        text = re.sub(r'\[.*?\]', '', text)
        text = re.sub(r"\\W"," ",text) 
        text = re.sub(r'https?://\S+|www\.\S+', '', text)
        text = re.sub(r'<.*?>+', '', text)
        text = re.sub(r'[%s]' % re.escape(string.punctuation), '', text)
        text = re.sub(r'\n', '', text)
        text = re.sub(r'\w*\d\w*', '', text)    
        return text

    def predict_proba_pipeline(self, texts):
        cleaned_texts = [self.clean_text(t) for t in texts]
        vecs = self.vectorizer.transform(cleaned_texts)
        return self.model.predict_proba(vecs)
        
    def predict(self, raw_text):
        if not self.is_loaded:
            return {"error": "Model not loaded. Please run train_model.py first."}
            
        cleaned = self.clean_text(raw_text)
        vec = self.vectorizer.transform([cleaned])
        pred = self.model.predict(vec)[0]
        probs = self.model.predict_proba(vec)[0]
        
        confidence = float(probs[pred])
        cls_name = "Fake" if pred == 1 else "True"
        
        # Explain with LIME
        # explain_instance takes the raw string and a function that outputs probabilities
        try:
            exp = self.explainer.explain_instance(raw_text, self.predict_proba_pipeline, num_features=10)
            explanation = exp.as_list()
        except Exception as e:
            explanation = []
            print(f"LIME explanation failed: {e}")
            
        return {
            "prediction": cls_name,
            "confidence": confidence,
            "explanation": explanation,
            "cleaned_text": cleaned
        }

def extract_text_from_url(url):
    try:
        article = Article(url)
        article.download()
        article.parse()
        return article.text
    except Exception as e:
        print(f"Error extracting URL: {e}")
        return None

def extract_text_from_pdf(pdf_path):
    text = ""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                extracted = page.extract_text()
                if extracted:
                    text += extracted + "\n"
        return text
    except Exception as e:
        print(f"Error extracting PDF: {e}")
        return None
