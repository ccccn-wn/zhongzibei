import json
import numpy as np
import copy

WEIGHT_MOVABLE = 5
WEIGHT_BLOCK = 65536
class Info :
    def __init__(self) -> None:
        self.my_id = None
        self.enemy_id = None
        self.my_status = None
        self.enemy_status = None
        self.round = None
        self.map_info = np.zeros((15,15,5), dtype=np.int64) # 炸弹，固定障碍，可清除障碍，道具, 炸弹范围
        self.blockarea = np.zeros((15,15), dtype=np.int64)
        self.weightmap = np.zeros((15,15), dtype=np.int64)
        self.blocklist = []
        self.new_frame = False
    def update(self, resp_info : dict) -> None :
        self.my_id = resp_info['player_id']
        self.round = resp_info['round']
        new_map_info = np.zeros_like(self.map_info)
        for block in resp_info['map'] :
            is_Bomb =0
            is_Block = 0
            is_MoveBlock = 0
            is_Item = 0
            Bomb_range = 0
            for obj in block['objs'] :
                Bomb_range = obj['property']['bomb_range'] if obj['type'] == 2 else 0
                is_Bomb = 1 if obj['type'] == 2 else 0
                is_Block = 1 if obj['type'] == 3 and obj['property']['removable'] == False else 0
                is_MoveBlock = 1 if obj['type'] == 3 and obj['property']['removable'] == True else 0
                is_Item = obj['property']['item_type'] if obj['type'] == 4 else 0
                if obj['type'] == 1 : # is player
                    player_status = obj['property']
                    if player_status['player_id'] == self.my_id :
                        self.my_status = player_status
                        self.my_status['x'] = block['x']
                        self.my_status['y'] = block['y']
                    else :
                        self.enemy_status = player_status
                        self.enemy_id = player_status['player_id']
                        self.enemy_status['x'] = block['x']
                        self.enemy_status['y'] = block['y']
            new_map_info[block['x'], block['y'],0] = is_Bomb
            new_map_info[block['x'], block['y'],1] = is_Block
            new_map_info[block['x'], block['y'],2] = is_MoveBlock
            new_map_info[block['x'], block['y'],3] = is_Item
            new_map_info[block['x'], block['y'],4] = Bomb_range

        self.map_info = new_map_info
        self.blockarea = self.map_info[:,:,0:3].sum(axis = 2)
        # self.weightmap = self.blockarea * WEIGHT_BLOCK + self.map_info[:,:,2] * WEIGHT_MOVABLE
        # self.weightmap[self.my_status['x'],self.my_status['y']] = 0
        self.blocklist = self.generate_blocklist()
        self.get_distance_map()

        self.new_frame = True

    def is_new_frame(self) :
        if self.new_frame == True :
            self.new_frame = False
            return True
        else :
            return False

    def generate_blocklist(self):
        blocklist = []
        for x in range(15):
            for y in range(15):
                if self.blockarea[x,y] > 0 :
                    blocklist.append((x,y))
        # blocklist = np.nonzero(self.blockarea)

        return blocklist

    def get_distance_map(self) -> np.ndarray :
        new_distance_map = -np.ones((15,15), dtype=np.int64)
        new_distance_map[self.my_status['x'], self.my_status['y']] = 0
        distance_map = np.zeros_like(new_distance_map)
        block_map = self.map_info[:,:,0] + self.map_info[:,:,1] + self.map_info[:,:,2]
        step = 0
        while (new_distance_map != distance_map).any() : # 还有区域未计算
            distance_map = copy.deepcopy(new_distance_map)
            edges = np.where(distance_map == step)
            edges = zip(edges[0], edges[1])
            for point in edges :
                for x_bias in [-1,1] :
                    dst_point = (point[0] + x_bias, point[1])
                    if (min(dst_point) >= 0 and max(dst_point) < 15) and block_map[dst_point] == 0 and new_distance_map[dst_point] == -1:
                        new_distance_map[dst_point] = step + 1 
                for y_bias in [-1,1] :
                    dst_point = (point[0], point[1] + y_bias)
                    if (min(dst_point) >= 0 and max(dst_point) < 15) and block_map[dst_point] == 0 and new_distance_map[dst_point] == -1:
                        new_distance_map[dst_point] = step + 1

            step += 1
        # print(distance_map)
        return distance_map
    
    def get_danger_map(self) -> np.ndarray :
        danger_map = np.zeros((15,15))
        block_map = self.map_info[:,:,1]
        bomb_poses = np.where(self.map_info[:,:,4] != 0)
        bomb_poses = zip(bomb_poses[0], bomb_poses[1])
        for bomb_pos in bomb_poses :
            danger_map[bomb_pos] = 1
            bomb_range = self.map_info[:,:,4][bomb_pos]
            for x_bias in range(1,bomb_range + 1) :
                dst_point = (bomb_pos[0] + x_bias, bomb_pos[1])
                if max(dst_point) < 15 and block_map[dst_point] == 0 :
                    danger_map[dst_point] = 1
                else :
                    break
            for x_bias in range(-(bomb_range), 0) :
                dst_point = (bomb_pos[0] + x_bias, bomb_pos[1])
                if min(dst_point) >= 0 and block_map[dst_point] == 0 :
                    danger_map[dst_point] = 1
                else :
                    break

            for y_bias in range(1,bomb_range + 1) :
                dst_point = (bomb_pos[0], bomb_pos[1] + y_bias)
                if max(dst_point) < 15 and block_map[dst_point] == 0 :
                    danger_map[dst_point] = 1
                else :
                    break
            for y_bias in range(-(bomb_range), 0) :
                dst_point = (bomb_pos[0], bomb_pos[1] + y_bias)
                if min(dst_point) >= 0 and block_map[dst_point] == 0 :
                    danger_map[dst_point] = 1
                else :
                    break
        return danger_map

    def get_worthest_pos(self, danger_map = None) -> tuple :
        distance_map = self.get_distance_map()
        remove_map = self.map_info[:,:,2]
        block_map = self.map_info[:,:,1]
        available_map = np.zeros_like(distance_map)
        # available_map[distance_map == -1] = 0
        available_map[distance_map >= 0] = 1

        if danger_map is None :
            danger_map = np.zeros_like(available_map)
        available_map[danger_map == 1] = 0

        available_poses = np.where(available_map == 1) # 2xN
        available_poses = zip(available_poses[0], available_poses[1])
        worth_map = np.zeros_like(available_map)

        bomb_range = self.my_status['bomb_range']
        for available_pos in available_poses :
            available_pos = available_pos
            for x_bias in range(1,bomb_range + 1) :
                dst_pos = (available_pos[0] + x_bias, available_pos[1])
                if max(dst_pos) < 15 and block_map[dst_pos] == 0 :
                    worth_map[available_pos] += remove_map[dst_pos]
                else :
                    break
            for x_bias in range(-(bomb_range), 0) :
                dst_pos = (available_pos[0] + x_bias, available_pos[1])
                if min(dst_pos) >= 0 and block_map[dst_pos] == 0 :
                    worth_map[available_pos] += remove_map[dst_pos]
                else :
                    break
            for y_bias in range(1,bomb_range + 1) :
                dst_pos = (available_pos[0], available_pos[1] + y_bias)
                if max(dst_pos) < 15 and block_map[dst_pos] == 0 :
                    worth_map[available_pos] += remove_map[dst_pos]
                else :
                    break
            for y_bias in range(-(bomb_range), 0) :
                dst_pos = (available_pos[0], available_pos[1] + y_bias)
                if min(dst_pos) >= 0 and block_map[dst_pos] == 0 :
                    worth_map[available_pos] += remove_map[dst_pos]
                else :
                    break

        # #距离加权
        # worth_map *= get_weight(available_map)
        self.worthest_pos = np.unravel_index(np.argmax(worth_map, axis=None), worth_map.shape)
        return self.worthest_pos






        