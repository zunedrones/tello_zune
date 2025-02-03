from setuptools import setup, find_packages

setup(
    name="tello_zune",
    version="0.2",
    author="Zune Drones",
    author_email="zunedrones@gmail.com",
    description="Biblioteca tello-zune, serve para controlar, e obter informacoes do drone DJI Tello.",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/zunedrones/tello_zune",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GPL-3.0 license",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.9',
    install_requires=[
        'opencv-python'
    ],
)
