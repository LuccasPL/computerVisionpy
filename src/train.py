# src/train.py

import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Conv2D, MaxPooling2D, Flatten, Dense
from tensorflow.keras.preprocessing.image import ImageDataGenerator

def build_model(input_shape=(416, 416, 3), num_classes=80):
    # Exemplo simplificado de CNN (para detecção real, geralmente usa-se uma arquitetura mais robusta)
    model = Sequential([
        Conv2D(32, (3, 3), activation='relu', input_shape=input_shape),
        MaxPooling2D(pool_size=(2, 2)),
        Conv2D(64, (3, 3), activation='relu'),
        MaxPooling2D(pool_size=(2, 2)),
        Flatten(),
        Dense(128, activation='relu'),
        Dense(num_classes, activation='softmax')
    ])
    model.compile(optimizer='adam', loss='categorical_crossentropy', metrics=['accuracy'])
    return model

def train_model():
    # Criação dos data generators (ajuste os diretórios conforme sua estrutura)
    train_datagen = ImageDataGenerator(rescale=1./255, horizontal_flip=True, validation_split=0.2)
    train_generator = train_datagen.flow_from_directory(
        'data/processed/',
        target_size=(416, 416),
        batch_size=8,
        class_mode='categorical',
        subset='training'
    )
    validation_generator = train_datagen.flow_from_directory(
        'data/processed/',
        target_size=(416, 416),
        batch_size=8,
        class_mode='categorical',
        subset='validation'
    )
    
    model = build_model()
    model.summary()
    
    # Treinamento
    model.fit(
        train_generator,
        epochs=10,
        validation_data=validation_generator
    )
    
    # Salvar o modelo treinado
    model.save("models/custom_model.h5")
    print("Modelo treinado e salvo em models/custom_model.h5")

if __name__ == "__main__":
    train_model()
