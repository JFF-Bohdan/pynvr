echo "Removing Python compiled files"
del /F /Q .\*.pyc
del /F /Q .\system\*.pyc
del /F /Q .\__pycache__\*.pyc

echo "Removing logs"
del /F /Q .\logs\*.log*
echo "not empty" > .\logs\.no_empty

echo "Removing ALL video data"
del /F /Q .\video\*
RD /S /Q .\video
mkdir .\video
echo "not empty" > .\video\.no_empty

echo "Done"