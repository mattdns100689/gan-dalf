from __future__ import print_function, division
from keras.datasets import mnist
from keras.layers import Input, Dense, Reshape, Flatten, Dropout
from keras.layers import Activation, LeakyReLU
from keras.layers import BatchNormalization, Activation, ZeroPadding2D, MaxPooling2D
from keras.layers.convolutional import UpSampling2D, Conv2D, Conv2DTranspose
from keras.models import Sequential, Model, load_model
from keras.optimizers import Adam
import matplotlib.pyplot as plt
import sys, pdb, cv2
from loader import Loader

import numpy as np


class GAN():
    def __init__(self,load):
        self.load = load 
        self.img_rows = 32 
        self.img_cols = 32 
        self.channels = 3
        self.img_shape = (self.img_rows, self.img_cols,self.channels)
        self.latent_dim = 16**2 

        optimizer = Adam(0.0002, 0.5)

        # Build and compile the discriminator
        self.discriminator = self.build_discriminator()
        self.discriminator.compile(loss='binary_crossentropy',
            optimizer=optimizer,
            metrics=['accuracy'])

        # Build the generator
        if self.load == True:
            print('loaded generator')
            self.generator = load_model('gen.h5')
        else:
            self.generator = self.build_generator()

        # The generator takes noise as input and generates imgs
        z = Input(shape=(self.latent_dim,))
        img = self.generator(z)

        # For the combined model we will only train the generator
        self.discriminator.trainable = False

        # The discriminator takes generated images as input and determines validity
        validity = self.discriminator(img)

        # The combined model  (stacked generator and discriminator)
        # Trains the generator to fool the discriminator
        self.combined = Model(z, validity)
        self.combined.compile(loss='binary_crossentropy', optimizer=optimizer)

    def build_generator(self):

        noise = np.random.normal(0, 1, (1, self.latent_dim))
        model = Sequential()
        convT = Conv2DTranspose
        width = int(np.sqrt(self.latent_dim))

        model.add(Dense(512,input_shape=(self.latent_dim,)))
        model.add(LeakyReLU(0.2))
        model.add(BatchNormalization(momentum=0.8))

        model.add(Dense(512))
        model.add(LeakyReLU(0.2))
        model.add(BatchNormalization(momentum=0.8))

        model.add(Dense(1024))
        model.add(LeakyReLU(0.2))
        model.add(BatchNormalization(momentum=0.8))

        model.add(Dense(np.prod(self.img_shape)))
        model.add(LeakyReLU(0.2))
        model.add(Reshape(self.img_shape))
        model.add(Activation('tanh'))

        print(10*'*'+'Generator'+10*'*')
        model.summary()

        noise = Input(shape=(self.latent_dim,))
        img = model(noise)

        return Model(noise, img)

    def build_discriminator(self):

        model = Sequential()
        model.add(Flatten(input_shape=(self.channels,self.img_cols,self.img_rows,)))
        model.add(Dense(512))
        model.add(LeakyReLU(0.2))
        model.add(Dense(256))
        model.add(LeakyReLU(0.2))

        model.add(Dense(1, activation='sigmoid'))
        print(10*'*'+'Discriminator '+10*'*')
        model.summary()

        img = Input(shape=self.img_shape)
        validity = model(img)

        return Model(img, validity)

    def train(self, epochs, batch_size=128, sample_interval=50):

        def mnist():
            (X_train, _), (_, _) = mnist.load_data()
            X_train = X_train / 127.5 - 1.
            X_train = np.expand_dims(X_train, axis=3)
            return X_train

        dgen = Loader()
        dgenerator = dgen.data_gen()

        X_train = next(dgenerator)
        X_train = X_train[0]
        X_train = np.expand_dims(X_train,0)
        X_train = np.tile(X_train,(50,1,1,1))
        valid = np.ones((batch_size, 1))
        fake = np.zeros((batch_size, 1))
        noise = np.random.normal(0, 1, (batch_size, self.latent_dim))
        cv2.imwrite('train_images/eg.jpg',dgen.img_norm(X_train[0],inverse=True).astype(np.uint8))
            
        for epoch in range(epochs):

            # ---------------------
            #  Train Discriminator
            # ---------------------

            # Select a random batch of images
            idx = np.random.randint(0, X_train.shape[0], batch_size)
            imgs = X_train[idx]



            # Generate a batch of new images
            gen_imgs = self.generator.predict(noise)

            # Train the discriminator
            d_loss_real = self.discriminator.train_on_batch(imgs, valid)
            d_loss_fake = self.discriminator.train_on_batch(gen_imgs, fake)
            d_loss = 0.5 * np.add(d_loss_real, d_loss_fake)

            # ---------------------
            #  Train Generator
            # ---------------------

            noise = np.random.normal(0, 1, (batch_size, self.latent_dim))

            # Train the generator (to have the discriminator label samples as valid)
            g_loss = self.combined.train_on_batch(noise, valid)

            # Plot the progress
            print ("%d [D loss: %f, acc.: %.2f%%] [G loss: %f]" % (epoch, d_loss[0], 100*d_loss[1], g_loss))

            # If at save interval => save generated image samples
            if epoch % sample_interval == 0:
                self.sample_images(epoch)
            if epoch % 1000 == 0:
                print("Saving")
                self.generator.save('gen.h5')
                self.combined.save('model.h5')


    def sample_images(self, epoch, n = 5):
        r, c = n, n 
        noise = np.random.normal(0, 1, (r * c, self.latent_dim))
        gen_imgs = self.generator.predict(noise)
        real_or_fake = self.discriminator.predict(gen_imgs)
        sorted_idx = np.argsort(real_or_fake.squeeze()) # sort by validity
        real_or_fake = real_or_fake[sorted_idx]
        gen_imgs = gen_imgs[sorted_idx]


        # Rescale images 0 - 1
        gen_imgs = 0.5 * gen_imgs + 0.5

        fig, axs = plt.subplots(r, c,figsize=(20,20))
        cnt = 0
        for i in range(r):
            for j in range(c):
                axs[i,j].set_title('V={0:.2f}'.format(real_or_fake[cnt][0]))
                axs[i,j].imshow(gen_imgs[cnt, :,:,0], cmap='gray')
                axs[i,j].axis('off')
                cnt += 1
        fig.savefig("images/%d.png" % epoch)
        plt.close()


    def inference(self):
        pass


if __name__ == '__main__':
    inference = False
    train = True 
    if train == True:
        gan = GAN(load=False)
        gan.train(epochs=30000, batch_size=32, sample_interval=200)
    if inference == True:
        gan = GAN(load=True)
        gan.sample_images(-1,n=10)

