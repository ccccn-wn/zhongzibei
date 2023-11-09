import math
from resp_anaylise import Info

class Map(object):
    def __init__(self, mapsize):
        self.mapsize = mapsize

    def generate_cell(self, cell_width, cell_height):
        '''
        定义一个生成器，用来生成地图中的所有节点坐标
        :param cell_width: 节点宽度
        :param cell_height: 节点长度
        :return: 返回地图中的节点
        '''
        x_cell = -cell_width
        for num_x in range(self.mapsize[0] // cell_width):
            y_cell = -cell_height
            x_cell += cell_width
            for num_y in range(self.mapsize[1] // cell_height):
                y_cell += cell_height
                yield (x_cell, y_cell)

class Node(object):
    def __init__(self, pos):
        self.pos = pos
        self.father = None
        self.gvalue = 0
        self.fvalue = 0

    def compute_fx(self, enode, father):

        gx_father = father.gvalue
        #采用欧式距离计算父节点到当前节点的距离
        gx_f2n = math.sqrt((father.pos[0] - self.pos[0])**2 + (father.pos[1] - self.pos[1])**2)
        gvalue = gx_f2n + gx_father

        hx_n2enode = math.sqrt((self.pos[0] - enode.pos[0])**2 + (self.pos[1] - enode.pos[1])**2)
        fvalue = gvalue + hx_n2enode
        return gvalue, fvalue

    def set_fx(self, enode, father):
        self.gvalue, self.fvalue = self.compute_fx(enode, father)
        self.father = father

    def update_fx(self, enode, father):
        gvalue, fvalue = self.compute_fx(enode, father)
        if fvalue < self.fvalue:
            self.gvalue, self.fvalue = gvalue, fvalue
            self.father = father

class AStar(object):
    def __init__(self, info:Info, tar_pos):
        self.mapsize = (15,15) #表示地图的投影大小，并非屏幕上的地图像素大小
        self.openlist, self.closelist = [], []

        self.blocklist = info.blocklist

        self.snode = Node((info.my_status['x'], info.my_status['y'])) #用于存储路径规划的起始节点

        self.enode = Node(tar_pos) #用于存储路径规划的目标节点
        self.cnode = self.snode   #用于存储当前搜索到的节点

        
    def run(self):
        self.openlist.append(self.snode)
        while(len(self.openlist) > 0):
            #查找openlist中fx最小的节点
            fxlist = list(map(lambda x: x.fvalue, self.openlist))
            index_min = fxlist.index(min(fxlist))
            self.cnode = self.openlist[index_min]
            del self.openlist[index_min]
            self.closelist.append(self.cnode)

            # 扩展当前fx最小的节点，并进入下一次循环搜索
            self.extend(self.cnode)

            # 如果openlist列表为空，或者当前搜索节点为目标节点，则跳出循环
            if len(self.openlist) == 0 or self.cnode.pos == self.enode.pos:
                break

        if self.cnode.pos == self.enode.pos:
            self.enode.father = self.cnode.father
            return 1
        else:
            return -1

    def get_minroute(self):
        minroute = []
        current_node = self.enode

        while(True):
            minroute.append(current_node.pos)
            current_node = current_node.father
            if current_node.pos == self.snode.pos:
                break

        minroute.append(self.snode.pos)
        minroute.reverse()
        return minroute

    def extend(self, cnode):
        nodes_neighbor = self.get_neighbor(cnode)
        for node in nodes_neighbor:
            if node.pos in list(map(lambda x:x.pos, self.closelist)) or node.pos in self.blocklist:
                continue
            else:
                if node.pos in list(map(lambda x:x.pos, self.openlist)):
                    node.update_fx(self.enode, cnode)
                else:
                    node.set_fx(self.enode, cnode)
                    self.openlist.append(node)

    def get_neighbor(self, cnode):
        offsets = [(1,0),(0,-1),(0,1),(-1,0)]
        nodes_neighbor = []
        x, y = cnode.pos[0], cnode.pos[1]
        for os in offsets:
            x_new, y_new = x + os[0], y + os[1]
            pos_new = (x_new, y_new)
            #判断是否在地图范围内,超出范围跳过
            if x_new < 0 or x_new > self.mapsize[0] - 1 or y_new < 0 or y_new > self.mapsize[1]:
                continue
            nodes_neighbor.append(Node(pos_new))

        return nodes_neighbor


# def main():
#     # mapsize = tuple(map(int, input('请输入地图大小，以逗号隔开：').split(',')))
#     # pos_snode = tuple(map(int, input('请输入起点坐标，以逗号隔开：').split(',')))
#     # pos_enode = tuple(map(int, input('请输入终点坐标，以逗号隔开：').split(',')))
#     # myAstar = AStar(info, tatpos)

#     # routelist = [] #记录搜索到的最优路径

#     # if myAstar.run() == 1:
#     #     routelist = myAstar.get_minroute()
#     #     print(routelist)
#     # else:
#     #     print('路径规划失败！')

