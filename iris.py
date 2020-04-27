import numpy as np
import struct
import seaborn as sn
import pandas as pd
import matplotlib.pyplot as plt

def load_dataset():
    sample_label_pairs = [] # [ (sample, label) ]

    with open(f'./iris_dataset.csv', 'rb') as csv_file:
        for row in csv_file:
            cells = [ cell.strip() for cell in row.decode().split(',') ]

            label = cells[ len(cells)-1 ]
            sample = np.array(cells[ :len(cells)-1], dtype=np.float32)

            sample_label_pairs.append( (sample, label) )

    sample_label_pairs = np.array(sample_label_pairs)
    samples, labels = np.transpose(sample_label_pairs)

    return samples, labels


def split_dataset(samples, labels, split_index):
    classes = np.unique(labels)

    indices_by_class = []
    for curr_class in classes:
        indices = np.where(labels == curr_class)[0]
        indices_by_class.append(indices)
    indices_by_class = np.array(indices_by_class)

    first_set_indices_by_class = indices_by_class[ :, :split_index ]
    last_set_indices_by_class = indices_by_class[ :, split_index:]

    first_set_indices = first_set_indices_by_class.flatten()
    last_set_indices = last_set_indices_by_class.flatten()

    first_set = samples.take(first_set_indices), labels.take(first_set_indices)
    last_set = samples.take(last_set_indices), labels.take(last_set_indices)

    return first_set, last_set


######################################
#      -- LINEAR CLASSIFIER --       #
######################################

# Implements eq. (3.20) using
# samples = x
# Returns vectors such as [0.321 0.485 0.843]^T
def get_predicted_label_vectors(samples, W):
    exponentials = np.array([ np.exp(-(np.matmul(W, sample))) for sample in samples ])
    denominators = exponentials + 1
    predictions = 1 / denominators

    return predictions

# Finds the class which is closest to a given label vector
# i.e.: [0.321 0.485 0.843]^T returns [0 0 1]^T
def get_rounded_label_vector(label_vector):
    index = np.argmax(label_vector)
    rounded_vector_label = np.array([ i == index for i in range(len(label_vector)) ], dtype=np.uint8)

    return rounded_vector_label

# Implements eq. (3.22) and eq. (3.23) using
# predicted_labels[k] = g_k
# labels[k] = t_k
# samples = x
# previous_W = W(m - 1)
# ASSUMES: len(predicted_labels) = len(labels) = len(samples)
def get_next_weight_matrix(predicted_labels, labels, samples, previous_W, alpha=0.01):
    num_features = len(samples[0]) - 1 # Subtract 1 because of the 1-fill
    num_classes = 3
    grad_g_MSE = predicted_labels - labels # dim (30,3)
    grad_z_g = predicted_labels * (1 - predicted_labels) # dim (30,3)

    grad_W_z = np.array([ np.reshape(sample, (1, num_features+1)) for sample in samples ])

    grad_W_MSE = np.sum( np.matmul(np.reshape(grad_g_MSE[k] * grad_z_g[k], (num_classes, 1)), grad_W_z[k]) for k in range(len(grad_g_MSE)) )

    next_W = previous_W - alpha * grad_W_MSE

    return next_W

# This function uses train_samples and train_labels to train a  linear classifier
# For each iteration, it outputs its error rate by comparing against
# the test set (test_samples, test_labels)
# It outputs the weighing matrix W and the rate of errors per iteration
def train_linear_classifier(train_samples, train_label_vectors, test_samples, test_label_vectors, features, num_iterations=1000, alpha=0.01):
    classes = np.unique(train_label_vectors)
    num_classes = 3
    num_features = len(features)

    MSE_per_iteration = []
    error_rate_per_iteration = []

    # Initialize weight matrix
    W = np.zeros((num_classes, num_features+1))

    for curr_iteration in range(num_iterations):
        # Training
        predicted_train_label_vectors = get_predicted_label_vectors(train_samples, W)
        W = get_next_weight_matrix(predicted_train_label_vectors, train_label_vectors, train_samples, W, alpha)

        # Testing
        predicted_test_label_vectors = get_predicted_label_vectors(test_samples, W)
        predicted_test_label_vectors_rounded = np.array([ \
            get_rounded_label_vector(label_vector) \
            for label_vector in predicted_test_label_vectors \
        ])

        curr_MSE = get_MSE(predicted_test_label_vectors, test_label_vectors)
        MSE_per_iteration.append(curr_MSE)

        curr_error_rate = get_error_rate(predicted_test_label_vectors_rounded, test_label_vectors)
        error_rate_per_iteration.append(curr_error_rate)

    return W, np.array(MSE_per_iteration), np.array(error_rate_per_iteration)

# Implements eq. (3.19) using
# predicted_label_vectors[k] = g_k
# true_label_vectors[k] = t_k
def get_MSE(predicted_label_vectors, true_label_vectors):
    error = predicted_label_vectors - true_label_vectors
    error_T = np.transpose(error)
    return np.sum(np.matmul(error_T,error)) / 2

# Assumes that predicted_label_vectors are rounded
# using get_rounded_label_vector
def get_error_rate(predicted_label_vectors, true_label_vectors):
    num_samples = len(true_label_vectors)
    classes = np.unique(true_label_vectors)

    num_errors = 0
    for i in range(len(true_label_vectors)):
        if not np.array_equal(true_label_vectors[i], predicted_label_vectors[i]):
            num_errors += 1

    return num_errors / num_samples

def get_confusion_matrix(predicted_labels, labels):
    classes = np.unique(labels)

    confusion_matrix = []
    for predicted_class in classes:
        row = []

        for true_class in classes:
            # All occurences of current true_class in labels_true:
            true_indices = np.where(labels == true_class)[0]

            # All occurences of current predicted_class in labels_predicted:
            predicted_indices = np.where(predicted_labels == predicted_class)[0]

            # We want to find the number of elements where these two matches:
            num_occurences = len( np.intersect1d(true_indices, predicted_indices) )
            row.append(num_occurences)

        confusion_matrix.append(row)

    return np.array(confusion_matrix)

def label_string_to_vector(string_label, classes):
    index = np.where(classes == string_label)[0]
    vector_label = np.array([ i == index for i in range(len(classes)) ], dtype=np.uint8)
    vector_label = np.reshape(vector_label, len(vector_label))

    return vector_label

def label_vector_to_string(vector_label, classes):
    index = np.argmax(vector_label)
    vector_string = classes[index]

    return vector_string

#######################################

def plot_histograms(samples, labels, features, step_length=0.1):
    classes = np.unique(labels)

    num_subplots = len(features)
    num_cols = np.uint8(np.floor(np.sqrt(num_subplots)))
    num_rows = np.uint8(np.ceil(num_subplots / num_cols))

    fig = plt.figure(figsize=(10, 10))

    for feature_index in range(len(features)):
        feature = features[feature_index]

        ax = fig.add_subplot(num_cols, num_rows, feature_index+1)
        ax.set(xlabel='Measurement [cm]', ylabel='Number of samples')

        for curr_class in classes:
            sample_indices = np.where(labels == curr_class)[0]

            samples_matching_class = [ samples[i] for i in sample_indices ]
            measurements_by_features = np.transpose(samples_matching_class)
            measurements_matching_feature = measurements_by_features[feature_index]

            ax.hist(measurements_matching_feature, alpha=0.5, stacked=True, label=curr_class)

        ax.set_title(feature)
        ax.legend(prop={'size': 7})

    plt.show()

def plot_confusion_matrix(confusion_matrix, classes, name="Confusion matrix"):
    df_cm = pd.DataFrame(confusion_matrix, index=classes, columns=classes)
    fig = plt.figure(figsize = (10,7))

    fig.suptitle(name, fontsize=16)

    sn.heatmap(df_cm, annot=True)

    plt.show()

def plot_MSEs(MSEs_per_alpha, alphas):
    for i in range(len(alphas)):
        MSEs = MSEs_per_alpha[i]
        alpha = alphas[i]

        iteration_numbers = range(len(MSEs))
        plt.plot(iteration_numbers, MSEs, label='$\\alpha={' + str(alpha) + '}$')

    plt.xlabel("Iteration number")
    plt.ylabel("MSE")
    plt.legend()

    plt.show()

def plot_error_rates(error_rates_per_alpha, alphas):
    for i in range(len(alphas)):
        error_rates = error_rates_per_alpha[i]
        alpha = alphas[i]
        print(error_rates[:10])

        iteration_numbers = range(len(error_rates))
        plt.plot(iteration_numbers, error_rates, label='$\\alpha={' + str(alpha) + '}$')

    plt.xlabel("Iteration number")
    plt.ylabel("Error rate")
    plt.legend()

    plt.show()


def main():
    all_samples, all_labels = load_dataset()

    # Map indices of features to human friendly names:
    features = {0: 'Sepal length',
                1: 'Sepal width',
                2: 'Petal length',
                3: 'Petal width'}
    plot_histograms(all_samples, all_labels, features)

    train_dataset, test_dataset = split_dataset(all_samples, all_labels, split_index=30)
    train_samples, train_labels = train_dataset
    test_samples, test_labels = test_dataset

    # We need to add an awkward 1 to x_k as described on page 15:
    train_samples = np.array([ np.append(sample, [1]) for sample in train_samples ])
    test_samples = np.array([ np.append(sample, [1]) for sample in test_samples ])

    classes = np.unique(train_labels)

    train_label_vectors = np.array([ label_string_to_vector(label, classes) for label in train_labels])
    test_label_vectors = np.array([ label_string_to_vector(label, classes) for label in test_labels])

    W, _, _ = train_linear_classifier( \
        train_samples, train_label_vectors, \
        train_samples, train_label_vectors, \
        features, num_iterations=300, alpha=0.005 \
    )

    alphas=[0.0025, 0.005, 0.0075, 0.01]
    MSEs_per_alpha = []
    error_rates_per_alpha = []
    for alpha in alphas:
        _, MSE_per_iteration, error_rate_per_iteration = train_linear_classifier( \
            train_samples, train_label_vectors, \
            test_samples, test_label_vectors, \
            features, alpha=alpha\
        )
        MSEs_per_alpha.append(MSE_per_iteration)
        error_rates_per_alpha.append(error_rate_per_iteration)

    print("Shape:", np.array(error_rates_per_alpha).shape)

    plot_MSEs(MSEs_per_alpha, alphas)
    plot_error_rates(error_rates_per_alpha, alphas)

    predicted_test_label_vectors = get_predicted_label_vectors(test_samples, W)
    predicted_test_label_vectors = np.array([ get_rounded_label_vector(label_vector) for label_vector in predicted_test_label_vectors ])

    predicted_test_label_strings = np.array([ label_vector_to_string(label, classes) for label in predicted_test_label_vectors ])

    error_rate = get_error_rate(predicted_test_label_vectors, test_label_vectors)
    print("Error rate:", error_rate)
    confusion_matrix = get_confusion_matrix(predicted_test_label_strings, test_labels)
    plot_confusion_matrix(confusion_matrix, classes)

main()