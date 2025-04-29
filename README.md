to run this project

install the requirements

pip install -r requirements.txt

then install tesseract ocr from

https://github.com/tesseract-ocr/tesseract/releases

make sure all the files are in the directory of the dataset names lbsmaske

finally run this command

uvicorn main:app --reload
