from flytekit import ImageSpec, task, workflow

image = ImageSpec(
    builder="fast-builder",
    conda_packages=["numpy", "scikit-learn==1.4.2", "samtools"],
    conda_channels=["bioconda"],
    registry="ghcr.io/thomasjpfan",
)


@task(container_image=image)
def train_model() -> float:
    from sklearn.datasets import load_iris
    from sklearn.model_selection import train_test_split
    from sklearn.tree import DecisionTreeClassifier

    X, y = load_iris(return_X_y=True)

    X_train, X_test, y_train, y_test = train_test_split(X, y, random_state=0)

    clf = DecisionTreeClassifier()
    clf.fit(X_train, y_train)

    return clf.score(X_test, y_test)


@workflow
def wf() -> float:
    return train_model()
