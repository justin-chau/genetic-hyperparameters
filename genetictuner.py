import tensorflow as tf
from tensorflow.python.keras.models import Sequential
from tensorflow.python.keras.layers import Dense, Dropout, Flatten

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.image as mpimg

from PIL import Image
from os import path
import pathlib

import random
import math

import json
from json.decoder import JSONDecodeError

class ModelTypes:
    TYPE_MLP = "MLP"
    TYPE_CNN = "CNN"

class GeneticTuner:
    def __init__(self, model_type):
        self.model_type = model_type
        self.population_parents = []
        self.population = []
        self.fitness_history = []

    def load_images(self, directory, show=False):
        self.full_directory = pathlib.Path(path.expanduser("~") + directory)
        self.class_names = np.array([item.name for item in self.full_directory.glob('*')])
        self.image_count = len(list(self.full_directory.glob('*/*.png')))
        self.image_height = self.get_class_example(self.class_names[0]).shape[0]
        self.image_width = self.get_class_example(self.class_names[0]).shape[1]
        self.print_message("Classes", self.class_names)
        self.print_message("Image Count", self.image_count)
    
    def display_batch(self):
        self.print_message("Notice", "Confirm that the images are labeled correctly and then exit.")
        image_generator = tf.keras.preprocessing.image.ImageDataGenerator(rescale=1./255)
        train_data_gen = image_generator.flow_from_directory(directory=str(self.full_directory),
                                                            batch_size=25,
                                                            target_size=(self.image_height, self.image_width),
                                                            classes = list(self.class_names))
        
        image_batch, label_batch = next(train_data_gen)
        plt.figure(figsize = (10,10))
        for n in range(25):
            ax = plt.subplot(5,5,n+1)
            plt.imshow(image_batch[n])
            plt.title(self.class_names[label_batch[n]==1][0].title())
            plt.axis('off')

        plt.show()

    def getRandomActivation(self):
        return random.choice(self.activation_in)

    def getRandomActivationOut(self):
        return random.choice(self.activation_out)

    def getRandomLossFunction(self):
        return random.choice(self.loss_function)

    def getRandomeOptimizer(self):
        return random.choice(self.optimizer)

    def getRandomChromosome(self):
        return [
                random.randint(1, self.nodes),
                random.randint(1, self.epochs),
                random.randint(1, self.batch_size),
                random.randint(0, self.hidden_layers),
                random.uniform(0.0, self.dropout),
                self.getRandomActivation(),
                self.getRandomActivationOut(),
                self.getRandomLossFunction(),
                self.getRandomeOptimizer()
            ]

    def initialize_population(self, population_size=10, tournamet_size=5, nodes=100,
                                epochs=100, batch_size=100, hidden_layers=5, dropout=0.5,
                                activation_in=['tanh', 'softmax', 'selu'], activation_out=['tanh', 'softmax', 'selu'], loss_function=['mse'], optimizer=['adam', 'sgd']):
        
        self.population_size = population_size
        self.tournamet_size = tournamet_size
        self.nodes = nodes
        self.epochs = epochs
        self.batch_size = batch_size
        self.hidden_layers = hidden_layers
        self.dropout = dropout
        self.activation_in = activation_in
        self.activation_out = activation_out
        self.loss_function = loss_function
        self.optimizer = optimizer

        for i in range(0, population_size):
            self.population.append(self.getRandomChromosome())
            
    def run_MLP(self, chromosome):
        # Implement Early Stopping
        self.print_message("Current Chromosome", chromosome)
        (nodes, epochs, batch_size, hidden_layers, dropout, act_in, act_out, loss_fcn, optimizer) = chromosome
        steps_per_epoch = np.ceil((self.image_count/batch_size)*.8)
        validation_steps = np.ceil((self.image_count/batch_size)*.2)
        image_generator = tf.keras.preprocessing.image.ImageDataGenerator(rescale=1./255, validation_split=0.2)
        train_data_gen = image_generator.flow_from_directory(directory=str(self.full_directory),
                                                            batch_size=batch_size,
                                                            target_size=(self.image_height, self.image_width),
                                                            classes = list(self.class_names),
                                                            subset="training")

        validation_data_gen = image_generator.flow_from_directory(directory=str(self.full_directory),
                                                                batch_size=batch_size,
                                                                target_size=(self.image_height, self.image_width),
                                                                classes = list(self.class_names),
                                                                subset="validation")

        model = Sequential()
        model.add(Flatten(input_shape=(self.image_height, self.image_width, 3)))

        model.add(Dense(nodes, activation=act_in))
        
        for i in range(hidden_layers):
            model.add(Dense(int(nodes/2), activation = act_in))
            model.add(Dropout(dropout))

        model.add(Dense(len(self.class_names), activation = act_out))

        model.compile(loss = loss_fcn, optimizer = optimizer)

        history = model.fit_generator(
            train_data_gen,
            steps_per_epoch=steps_per_epoch,
            epochs=epochs,
            validation_data=validation_data_gen,
            validation_steps=validation_steps
        )

        self.fitness_history.append((history.history['val_loss'][-1], chromosome))

    def run_tournament_selection(self):
        fittest_loss = math.inf
        fittest_chromosome = []
        for i in range(0, self.tournamet_size):
            random_index = random.randint(0, len(self.fitness_history)-1)
            if self.fitness_history[random_index][0] < fittest_loss:
                fittest_loss = self.fitness_history[random_index][0]
                fittest_chromosome = self.fitness_history[random_index][1]

        return fittest_chromosome
    
    def select_parents(self):
        for i in range(0, self.population_size):
            parents = []
            for j in range(0, 2):
                parents.append(self.run_tournament_selection())

            self.print_message("Parents Selected", parents)
            self.population_parents.append(parents)
        
        self.fitness_history = []

    def crossover(self):
        for i in range(0, len(self.population)):
            new_chromosome = self.population_parents[i][0][0:2] + self.population_parents[i][1][2:5] + self.population_parents[i][0][5:]
            self.population[i] = new_chromosome

            self.print_message("Chromosome Generated", self.population[i])

    def mutate(self, mutation_rate=0.015):
        for i in range(0, len(self.population)):
            random_chromosome = self.getRandomChromosome()
            for j in range(0, len(random_chromosome)):
                if random.random() < mutation_rate:
                    self.population[i][j] = random_chromosome[j]

    def run_tuner(self, generations=5):
        if self.model_type == ModelTypes.TYPE_MLP:

            for i in range(0, generations):
                self.print_message("New Generation", "Generation" + str(i))

                for chromosome in self.population:
                    self.run_MLP(chromosome)

                with open("generation{}.json".format(i), 'w') as f:
                    json.dump({"Generation" + str(i): self.fitness_history}, f)                    
                
                self.select_parents()
                self.crossover()
                self.mutate()

    def print_message(self, name, message):
        header = "---{}-----------------------".format(name)

        print("\n" + header)
        print(message)
        print("-"*len(header), end="\n\n")

    def get_image_count(self):
        return self.image_count

    def get_class_names(self):
        return self.class_names

    def get_population(self):
        return self.population

    def get_class_example(self, class_name):
        class_directory = list(self.full_directory.glob(class_name + "/*"))

        example_directory = class_directory[0]
        img = plt.imread(str(example_directory))
        return img