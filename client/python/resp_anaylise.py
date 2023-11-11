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
        self.map_info = np.zeros((15,15,4), dtype=np.int64) # 炸弹，固定障碍，可清除障碍，道具
        self.blockarea = np.zeros((15,15), dtype=np.int64)
        self.weightmap = np.zeros((15,15), dtype=np.int64)
        self.blocklist = []
    def update(self, resp_info : dict) -> None :
        self.my_id = resp_info['player_id']
        self.round = resp_info['round']
        new_map_info = np.zeros((15,15,4), dtype=np.int64)
        for block in resp_info['map'] :
            is_Bomb =0
            is_Block = 0
            is_MoveBlock = 0
            is_Item = 0
            for obj in block['objs'] :
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

        self.map_info = new_map_info
        self.blockarea = self.map_info[:,:,0:2].sum(axis = 2)
        self.weightmap = self.blockarea * WEIGHT_BLOCK + self.map_info[:,:,2] * WEIGHT_MOVABLE
        self.weightmap[self.my_status['x'],self.my_status['y']] = 0
        self.blocklist = self.generate_blocklist()
        self.get_distance_map()

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
                    dst_point = [point[0] + x_bias, point[1]]
                    if (min(dst_point) >= 0 and max(dst_point) < 15) and block_map[dst_point[0], dst_point[1]] == 0 and new_distance_map[dst_point[0], dst_point[1]] == -1:
                        new_distance_map[dst_point[0], dst_point[1]] = step + 1 
                for y_bias in [-1,1] :
                    dst_point = [point[0], point[1] + y_bias]
                    if (min(dst_point) >= 0 and max(dst_point) < 15) and block_map[dst_point[0], dst_point[1]] == 0 and new_distance_map[dst_point[0], dst_point[1]] == -1:
                        new_distance_map[dst_point[0], dst_point[1]] = step + 1

            step += 1
        print(distance_map)
        return distance_map

    def get_worthest_pos(self) -> tuple :
        distance_map = self.get_distance_map()
        available_map = np.zeros_like(distance_map)
        # available_map[distance_map == -1] = 0
        available_map[distance_map >= 0] = 1

        