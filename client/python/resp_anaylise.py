import json
import numpy as np
import copy

class Info :
    def __init__(self) -> None:
        self.my_id = None
        self.enemy_id = None
        self.my_status = None
        self.enemy_status = None
        self.round = None
        self.map_info = np.zeros((15,15,4), dtype=np.int64) # 炸弹，固定障碍，可清除障碍，道具

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

    def get_distance_map(self, remove = False) -> np.ndarray :
        distance_map = -np.ones((15,15), dtype=np.int64)
        distance_map[self.my_status['x'], self.my_status['y']] = 0
        new_distance_map = copy.deepcopy(distance_map)
        while (new_distance_map != distance_map).any() : # 还有区域未计算
            for x in new_distance_map.shape[0] :
                for y in new_distance_map.shape[1] :
                    block = new_distance_map[x,y]
                    if block == -1 :
                        continue
                    min_distance = np.min(block[x-1:x+2, y-1:y+2])[0]
                    if min_distance == -1 :
                        continue
                    new_distance_map[x,y] = min_distance + 1
                    
        