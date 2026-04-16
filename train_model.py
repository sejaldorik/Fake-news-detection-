import pandas as pd
import numpy as np
import pickle
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report
import re
import string

def clean_text(text):
    text = text.lower()
    text = re.sub(r'\[.*?\]', '', text)
    text = re.sub(r"\\W"," ",text) 
    text = re.sub(r'https?://\S+|www\.\S+', '', text)
    text = re.sub(r'<.*?>+', '', text)
    text = re.sub(r'[%s]' % re.escape(string.punctuation), '', text)
    text = re.sub(r'\n', '', text)
    text = re.sub(r'\w*\d\w*', '', text)    
    return text

def main():
    print("Loading datasets...")
    # Load the datasets
    fake_df = pd.read_csv('Fake.csv')
    true_df = pd.read_csv('True.csv')

    # Add labels (0 for True, 1 for Fake)
    fake_df['class'] = 1
    true_df['class'] = 0

    print("Data loaded. Combining and cleaning...")
    # Drop irrelevant columns and combine
    # Fake/True usually have title, text, subject, date
    fake_df = fake_df[['text', 'class']]
    true_df = true_df[['text', 'class']]

    df = pd.concat([fake_df, true_df], axis=0)

    # Shuffle the dataset
    df = df.sample(frac=1).reset_index(drop=True)

    # Note: we might want to clean the text, it can be very heavy though. 
    # To speed things up, we apply it to a sampled fraction if we want, but let's do all.
    # To prevent Memory errors and speed up training, we'll limit the dataset if it's too huge,
    # but 100MB of text is manageable on modern systems.
    print("Applying text cleaning...")
    df['text'] = df['text'].apply(clean_text)

    x = df['text']
    y = df['class']

    # Splitting data
    print("Splitting dataset into train and test...")
    x_train, x_test, y_train, y_test = train_test_split(x, y, test_size=0.25, random_state=42)

    # TF-IDF Vectorization
    print("Vectorizing text using TF-IDF...")
    vectorizer = TfidfVectorizer(max_features=10000) # limit features to save memory and size
    x_train_vec = vectorizer.fit_transform(x_train)
    x_test_vec = vectorizer.transform(x_test)

    # Training Model
    print("Training Logistic Regression Model...")
    model = LogisticRegression()
    model.fit(x_train_vec, y_train)

    # Evaluation
    pred = model.predict(x_test_vec)
    print("Model Evaluation:")
    print("Accuracy:", accuracy_score(y_test, pred))
    print(classification_report(y_test, pred))

    # Saving Model and Vectorizer
    print("Saving model.pkl and vectorizer.pkl...")
    with open('model.pkl', 'wb') as file:
        pickle.dump(model, file)
    
    with open('vectorizer.pkl', 'wb') as file:
        pickle.dump(vectorizer, file)
        
    print("Training complete and files saved successfully!")

if __name__ == '__main__':
    main()
