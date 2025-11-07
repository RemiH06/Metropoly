from bs4 import BeautifulSoup

def get_colors():
    with open('src/palette.html', 'r') as file:
        soup = BeautifulSoup(file, 'html.parser')
    
    colors = {
        "basicBG": soup.find('style').string.split("--basicBG:")[1].split(";")[0].strip(),
        "borderBlack": soup.find('style').string.split("--borderBlack:")[1].split(";")[0].strip(),
        "red": soup.find('style').string.split("--red:")[1].split(";")[0].strip(),
        "orange": soup.find('style').string.split("--orange:")[1].split(";")[0].strip(),
        "yellow": soup.find('style').string.split("--yellow:")[1].split(";")[0].strip(),
        "green": soup.find('style').string.split("--green:")[1].split(";")[0].strip(),
        "blue": soup.find('style').string.split("--blue:")[1].split(";")[0].strip(),
        "pink": soup.find('style').string.split("--pink:")[1].split(";")[0].strip(),
        "lightBlue": soup.find('style').string.split("--lightBlue:")[1].split(";")[0].strip(),
        "brown": soup.find('style').string.split("--brown:")[1].split(";")[0].strip(),
        "purple": soup.find('style').string.split("--purple:")[1].split(";")[0].strip(),
        "teal": soup.find('style').string.split("--teal:")[1].split(";")[0].strip(),
        "lavender": soup.find('style').string.split("--lavender:")[1].split(";")[0].strip(),
        "lightGreen": soup.find('style').string.split("--lightGreen:")[1].split(";")[0].strip(),
        "deepBlue": soup.find('style').string.split("--deepBlue:")[1].split(";")[0].strip(),
        "gold": soup.find('style').string.split("--gold:")[1].split(";")[0].strip(),
        "chineseRed": soup.find('style').string.split("--chineseRed:")[1].split(";")[0].strip()
    }
    
    return colors
