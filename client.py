# Библиотеки
import sys 
import pygame
import math
import random
from pygame.locals import *
import pygame_menu
import socket
import pickle # Для сериализации
import threading

pygame.init()

# Константы
DISPLAY_WIDTH   = 1280
DISPLAY_HEIGHT  = 720

udp_host = "127.0.0.1"	
udp_port = 1234			        

def collision(rleft, rtop, width, height,   
              center_x, center_y, radius): 
    """ Detect collision between a rectangle and circle. """

    rright, rbottom = rleft + width/2, rtop + height/2

    cleft, ctop     = center_x-radius, center_y-radius
    cright, cbottom = center_x+radius, center_y+radius

    if rright < cleft or rleft > cright or rbottom < ctop or rtop > cbottom:
        return False  

    for x in (rleft, rleft+width):
        for y in (rtop, rtop+height):
            if math.hypot(x-center_x, y-center_y) <= radius:
                return True  

    if rleft <= center_x <= rright and rtop <= center_y <= rbottom:
        return True  

    return False 

# Переменные
mainScreen = pygame.display.set_mode([DISPLAY_WIDTH, DISPLAY_HEIGHT])
pygame.display.set_caption("Agar.io")

mainClock = pygame.time.Clock() 

font        = pygame.font.SysFont('Ubuntu',20,True)
big_font    = pygame.font.SysFont('Ubuntu',24,True)

sock = None 

isWorking = True

remotePlayers = {}
localAddr = None
localZone = 0
zones = []
zones.append(pygame.Rect((0, 0, DISPLAY_WIDTH // 2 - 1, DISPLAY_HEIGHT // 2 - 1)))
zones.append(pygame.Rect((DISPLAY_WIDTH // 2, 0, DISPLAY_WIDTH // 2, DISPLAY_HEIGHT // 2)))
zones.append(pygame.Rect((0, DISPLAY_HEIGHT // 2, DISPLAY_WIDTH // 2 - 1, DISPLAY_HEIGHT // 2 - 1)))
zones.append(pygame.Rect((DISPLAY_WIDTH // 2, DISPLAY_HEIGHT // 2, DISPLAY_WIDTH // 2 - 1, DISPLAY_HEIGHT // 2 - 1)))

# Меню
menu = pygame_menu.Menu('Agar.io', DISPLAY_WIDTH, DISPLAY_HEIGHT, theme=pygame_menu.themes.THEME_BLUE)

def make_request(requestType, requestMessage):
    data = {
        "requestType": requestType,
        "requestMessage": requestMessage
    }
    sock.sendto(pickle.dumps(data),(udp_host,udp_port))

def handle_request(data):
    global localAddr, isWorking
    data = pickle.loads(data)
    requestType = data["requestType"]
    requestMessage = data["requestMessage"]
    if requestType == 1:
        data = data["requestMessage"]
        remotePlayer = RemotePlayer(mainScreen, player.camera, data[0], data[1], data[2], data[3], data[4], data[5], data[6], data[7])
        remotePlayers[data[8]] = remotePlayer
        make_request(2, [player.name, player.x, player.y, player.mass, player.speed, player.color, player.outlineColor, player.pieces, data[8], localAddr])  
    elif requestType == 2:
        data = data["requestMessage"]
        remotePlayer = RemotePlayer(mainScreen, player.camera, data[0], data[1], data[2], data[3], data[4], data[5], data[6], data[7])
        remotePlayers[data[9]] = remotePlayer
    elif requestType == 3:
        localAddr = requestMessage
    elif requestType == 4:
        data = data["requestMessage"]
        remotePlayers[data[0]].x = data[1]
        remotePlayers[data[0]].y = data[2]
        remotePlayers[data[0]].mass = data[3]
        remotePlayers[data[0]].speed = data[4]
        remotePlayers[data[0]].color = data[5]
        remotePlayers[data[0]].outlineColor = data[6]
        remotePlayers[data[0]].pieces = data[7]
        remotePlayers[data[0]].zone = data[8]
    elif requestType == 5:
        data = data["requestMessage"]
        loser = data[0]
        print(loser)
        print(localAddr)
        if loser == localAddr:
            isWorking = False
        else:
            if loser in enemies.copy():
                del enemies[loser]

def start_the_game():
    global gameState, menu, player, sock
    name = userNameTextInput.get_value()
    if len(name) < 4:
        print("Имя слишком короткое")
    else:
        menu.disable()
        sock = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
        player = Player(mainScreen, cam, name)
        make_request(1, [name, player.x, player.y, player.mass, player.speed, player.color, player.outlineColor, player.pieces])
        thread.start()

userNameTextInput = menu.add.text_input('Name :', default='Tester')
menu.add.button('Play', start_the_game)
menu.add.button('Quit', pygame_menu.events.EXIT)

def drawText(message,pos,color=(255,255,255)):
    mainScreen.blit(font.render(message,1,color),pos)

def getDistance(a, b):
    diffX = math.fabs(a[0]-b[0])
    diffY = math.fabs(a[1]-b[1])
    return ((diffX**2)+(diffY**2))**(0.5)


class Camera:
    def __init__(self):
        self.x = 0
        self.y = 0
        self.width = DISPLAY_WIDTH
        self.height = DISPLAY_HEIGHT
        self.zoom = 0.5

    def centre(self,blobOrPos):
        if isinstance(blobOrPos, Player):
            x, y = blobOrPos.x, blobOrPos.y
            self.x = (x - (x*self.zoom)) - x + (DISPLAY_WIDTH/2)
            self.y = (y - (y*self.zoom)) - y + (DISPLAY_HEIGHT/2)
        elif type(blobOrPos) == tuple:
            self.x, self.y = blobOrPos

    def update(self, target):
        self.zoom = 100/(target.mass)+0.3
        self.centre(player)


class Drawable:
    """ Абстрактный класс для обрисовки всех элементов
    """
    def __init__(self, surface, camera):
        self.surface = surface
        self.camera = camera

    def draw(self):
        pass

class Grid(Drawable):
    def __init__(self, surface, camera):
        super().__init__(surface, camera)
        self.color = (230,240,240)

    def draw(self):
        zoom = self.camera.zoom
        x, y = self.camera.x, self.camera.y
        for i in range(0,2001,25):
            pygame.draw.line(self.surface,  self.color, (x, i*zoom + y), (2001*zoom + x, i*zoom + y), 3)
            pygame.draw.line(self.surface, self.color, (i*zoom + x, y), (i*zoom + x, 2001*zoom + y), 3)

class Cell(Drawable): 
    """ Класс клеток которые игроки поднимают """
    CELL_COLORS = [ # Цвета для клеток
        (80,252,54),
        (36,244,255),
        (243,31,46),
        (4,39,243),
        (254,6,178),
        (255,211,7),
        (216,6,254),
        (145,255,7),
        (7,255,182),
        (255,6,86),
        (147,7,255)
    ]
    
    def __init__(self, surface, camera):
        super().__init__(surface, camera)
        self.x = random.randint(20,1980)
        self.y = random.randint(20,1980)
        self.mass = 7
        self.color = random.choice(Cell.CELL_COLORS)

    def draw(self):
        zoom = self.camera.zoom
        x,y = self.camera.x, self.camera.y
        center = (int(self.x*zoom + x), int(self.y*zoom + y))
        pygame.draw.circle(self.surface, self.color, center, int(self.mass*zoom))

class CellList(Drawable):
    """ Класс группирования клеток """
    def __init__(self, surface, camera, numOfCells):
        super().__init__(surface, camera)
        self.count = numOfCells
        self.list = []
        for i in range(self.count): self.list.append(Cell(self.surface, self.camera))

    def draw(self):
        for cell in self.list:
            cell.draw()

class Player(Drawable):
    """ Класс игрока
    """
    COLOR_LIST = [
    (37,7,255),
    (35,183,253),
    (48,254,241),
    (19,79,251),
    (255,7,230),
    (255,7,23),
    (6,254,13)]

    FONT_COLOR = (50, 50, 50)
    
    def __init__(self, surface, camera, name = ""):
        super().__init__(surface, camera)
        self.x = random.randint(100,400)
        self.y = random.randint(100,400)
        self.mass = 20
        self.speed = 4
        self.color = col = random.choice(Player.COLOR_LIST)
        self.outlineColor = (
            int(col[0]-col[0]/3),
            int(col[1]-col[1]/3),
            int(col[2]-col[2]/3))
        if name: self.name = name
        else: self.name = "Test"
        self.pieces = []
        self.zone = 0
        for i in range(len(zones)):
            if collision(zones[i].x, zones[i].y, zones[i].width, zones[i].height, self.x, self.y, self.mass/2):
                self.zone = i

    def collisionDetection(self, edibles):
        """ Проверка коллизии
        """
        for edible in edibles:
            if(getDistance((edible.x, edible.y), (self.x,self.y)) <= self.mass/2):
                self.mass+=0.5
                edibles.remove(edible)

    def collisionDetectionWithEnemies(self, enemies):
        for enemy in enemies.copy():
            if(getDistance((enemies[enemy].x, enemies[enemy].y), (self.x,self.y)) <= self.mass/2):
                self.mass+=0.5
                make_request(5, [enemy, localAddr])  
                del enemies[enemy]

    def move(self):
        """ Обновление позиции игрока
        """
        global localAddr
        if pygame.mouse.get_focused() != 0:
            dX, dY = pygame.mouse.get_pos()
            rotation = math.atan2(dY - float(DISPLAY_HEIGHT)/2, dX - float(DISPLAY_WIDTH)/2)
            rotation *= 180/math.pi
            normalized = (90 - math.fabs(rotation))/90
            vx = self.speed*normalized
            vy = 0
            if rotation < 0:
                vy = -self.speed + math.fabs(vx)
            else:
                vy = self.speed - math.fabs(vx)
            tmpX = self.x + vx
            tmpY = self.y + vy
            self.x = tmpX
            self.y = tmpY
            make_request(4, [localAddr, self.x, self.y, self.mass, self.speed, self.color, self.outlineColor, self.pieces, self.zone])  

    def draw(self):
        """ Отрисовка игрока
        """
        zoom = self.camera.zoom
        x, y = self.camera.x, self.camera.y
        center = (int(self.x*zoom + x), int(self.y*zoom + y))
        
        # Отрисовка круга вокруг игрока
        pygame.draw.circle(self.surface, self.outlineColor, center, int((self.mass/2 + 3)*zoom))
        # Отрисовка круга игрока
        pygame.draw.circle(self.surface, self.color, center, int(self.mass/2*zoom))
        # Отрисовка имени игрока
        fw, fh = font.size(self.name)
        drawText(self.name, (self.x*zoom + x - int(fw/2), self.y*zoom + y - int(fh/2)),
                 Player.FONT_COLOR)

class RemotePlayer(Drawable):
    FONT_COLOR = (50, 50, 50)
    
    def __init__(self, surface, camera, name, x, y, mass, speed, color, outlineColor, pieces):
        super().__init__(surface, camera)
        self.x = x
        self.y = y
        self.mass = mass
        self.speed =speed
        self.color = col = color
        self.outlineColor = outlineColor
        self.name = name
        self.pieces = pieces
        self.zone = 0

    def draw(self):
        """ Отрисовка игрока
        """
        zoom = self.camera.zoom
        x, y = self.camera.x, self.camera.y
        center = (int(self.x*zoom + x), int(self.y*zoom + y))
        
        # Отрисовка круга вокруг игрока
        pygame.draw.circle(self.surface, self.outlineColor, center, int((self.mass/2 + 3)*zoom))
        # Отрисовка круга игрока
        pygame.draw.circle(self.surface, self.color, center, int(self.mass/2*zoom))
        # Отрисовка имени игрока
        fw, fh = font.size(self.name)
        drawText(self.name, (self.x*zoom + x - int(fw/2), self.y*zoom + y - int(fh/2)),
                 Player.FONT_COLOR)

def thread_handling_request():
    while isWorking:
        try:
            data = sock.recvfrom(2048)
            handle_request(data[0])
        except Exception as ex:
            #print("Error: ", ex)
            pass

cam = Camera()

grid = Grid(mainScreen, cam)
cells = CellList(mainScreen, cam, 2000)
player = None

thread = threading.Thread(target=thread_handling_request)

while isWorking:
    mainClock.tick(60)
    events = pygame.event.get()
    for event in events:
        if event.type == QUIT:
            pygame.quit()
            isWorking = False
            quit()

    if menu.is_enabled():
        menu.mainloop(mainScreen)
    else:
        player.move()
        player.collisionDetection(cells.list)
        player.collisionDetectionWithEnemies(remotePlayers)
        cam.update(player)
        mainScreen.fill((255, 255, 255))
        grid.draw()
        cells.draw()
        player.draw()
        for i in range(len(zones)):
            if collision(zones[i].x, zones[i].y, zones[i].width, zones[i].height, player.x, player.y, player.mass/2):
                player.zone = i
        for i in remotePlayers:
            if remotePlayers[i].zone == player.zone:
                remotePlayers[i].draw()

    pygame.display.flip()