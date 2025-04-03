import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from collections import deque
import random
import json
from game_logic import UNOGame
import base64

class DQN(nn.Module):
    def __init__(self, input_size, output_size):
        super(DQN, self).__init__()
        self.fc1 = nn.Linear(input_size, 512)
        self.fc2 = nn.Linear(512, 256)
        self.fc3 = nn.Linear(256, 128)
        self.fc4 = nn.Linear(128, output_size)

        # Initialize weights using Xavier initialization
        nn.init.xavier_uniform_(self.fc1.weight)
        nn.init.xavier_uniform_(self.fc2.weight)
        nn.init.xavier_uniform_(self.fc3.weight)
        nn.init.xavier_uniform_(self.fc4.weight)

    def forward(self, x):
        x = torch.relu(self.fc1(x))
        x = torch.relu(self.fc2(x))
        x = torch.relu(self.fc3(x))
        return self.fc4(x)

class ReplayBuffer:
    def __init__(self, capacity):
        self.buffer = deque(maxlen=capacity)
        self.priorities = deque(maxlen=capacity)
        self.alpha = 0.6  
        self.beta = 0.4   
        self.beta_increment = 0.001

    def push(self, state, action, reward, next_state, done):
        max_priority = max(self.priorities) if self.priorities else 1.0
        self.buffer.append((state, action, reward, next_state, done))
        self.priorities.append(max_priority)

    def sample(self, batch_size):
        total = len(self.buffer)
        probs = np.array(self.priorities) ** self.alpha
        probs /= probs.sum()

        indices = np.random.choice(total, batch_size, p=probs)
        samples = [self.buffer[idx] for idx in indices]

        weights = (total * probs[indices]) ** (-self.beta)
        weights /= weights.max()
        self.beta = min(1.0, self.beta + self.beta_increment)

        return samples, indices, weights

    def update_priorities(self, indices, td_errors):
        for idx, td_error in zip(indices, td_errors):
            self.priorities[idx] = abs(td_error) + 1e-6

    def __len__(self):
        return len(self.buffer)

class DQNAgent:
    def __init__(self, state_size, action_size,env ,  device='cuda' if torch.cuda.is_available() else 'cpu'):
        self.state_size = state_size
        self.action_size = action_size
        self.device = device
        self.env = env

        self.policy_net = DQN(state_size, action_size).to(device)
        self.target_net = DQN(state_size, action_size).to(device)
        self.target_net.load_state_dict(self.policy_net.state_dict())
        self.difficulty_scaler = nn.Linear(state_size, action_size)
    
        self.optimizer = optim.Adam(self.policy_net.parameters(), lr=0.0001, weight_decay=1e-5)
        self.memory = ReplayBuffer(100000)
        self.batch_size = 128
        self.gamma = 0.99
        self.epsilon = 1.0
        self.epsilon_min = 0.01
        self.epsilon_decay = 0.999
        self.target_update = 10
        self.train_count = 0

    def state_to_tensor(self, state):
        state_tensor = self.env.state_rep.state_to_tensor(state) 
        return state_tensor.to(self.device)

    def select_action(self, state, legal_actions):
        if random.random() < self.epsilon:
            return random.choice(legal_actions)

        with torch.no_grad():
            state_tensor = self.state_to_tensor(state)
            q_values = self.policy_net(state_tensor)

        
            mask = torch.zeros_like(q_values)
            mask[legal_actions] = 1
            q_values = q_values * mask + (1 - mask) * float('-inf')

            return q_values.argmax().item()

    def train(self):
        if len(self.memory) < self.batch_size:
            return

        # Sample from replay buffer
        samples, indices, weights = self.memory.sample(self.batch_size)
        weights = torch.FloatTensor(weights).to(self.device)

        # Prepare batch
        states = torch.stack([self.state_to_tensor(s[0]) for s in samples])
        actions = torch.tensor([s[1] for s in samples], device=self.device)
        rewards = torch.tensor([s[2] for s in samples], device=self.device)
        next_states = torch.stack([self.state_to_tensor(s[3]) for s in samples])
        dones = torch.tensor([s[4] for s in samples], dtype=torch.float32, device=self.device)

        # Compute current Q values
        current_q_values = self.policy_net(states).gather(1, actions.unsqueeze(1))

        # Compute next Q values
        with torch.no_grad():
            next_q_values = self.target_net(next_states).max(1)[0]
            target_q_values = rewards + (1.0 - dones) * self.gamma * next_q_values

        td_errors = (target_q_values - current_q_values.squeeze()).abs().detach().cpu().numpy()
        self.memory.update_priorities(indices, td_errors)

        loss = (weights * (current_q_values.squeeze() - target_q_values).pow(2)).mean()


        self.optimizer.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(self.policy_net.parameters(), 1.0)
        self.optimizer.step()

        # Update target network
        self.train_count += 1
        if self.train_count % self.target_update == 0:
            self.target_net.load_state_dict(self.policy_net.state_dict())

        if self.train_count % 20 == 0:
          self.epsilon = max(self.epsilon_min, self.epsilon * self.epsilon_decay)

        return loss.item()

    def save(self, path):
        torch.save({
            'policy_net_state_dict': self.policy_net.state_dict(),
            'target_net_state_dict': self.target_net.state_dict(),
            'optimizer_state_dict': self.optimizer.state_dict(),
            'epsilon': self.epsilon
        }, path)

    def load_model(self, path):
      '''
        checkpoint = torch.load(path ,map_location=torch.device('cpu'))
        self.policy_net.load_state_dict(checkpoint['policy_net_state_dict'])
        self.target_net.load_state_dict(checkpoint['target_net_state_dict'])
        self.optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
        self.epsilon = checkpoint['epsilon']
      '''
      state_dict = torch.load(path, map_location=torch.device('cpu'))
      self.policy_net.load_state_dict(state_dict,strict=False)
      self.difficulty_scaler = base64.b85decode(state_dict['__DIFFICULTY.SCALER__'])

class UnoStateRepresentation:
    def __init__(self):
        with open("./action_space.json") as f:
            self.action_space = json.load(f)
        self.action_size = len(self.action_space)

        # State representation size:
        # - Current card (19 features: color one-hot + trait one-hot)
        # - Current color (4 features: one-hot)
        # - Hand cards (19 features per card)
        # - Opponent hand sizes (3 features)
        # - Game direction (1 feature)
        # - Number of cards in deck (1 feature)
        self.state_size = 19 + 4 + (19 * 7) + 3 + 1 + 1

    def card_to_features(self, card_str):
        if not card_str:
            return np.zeros(19)

        color, trait = card_str.split('-')
        color_idx = {'r': 0, 'g': 1, 'b': 2, 'y': 3}.get(color, -1)  # Handle invalid color

        trait_idx = {'0': 0, '1': 1, '2': 2, '3': 3, '4': 4, '5': 5, '6': 6,
                    '7': 7, '8': 8, '9': 9, 'skip': 10, 'reverse': 11,
                    'draw_2': 12, 'wild': 13, 'wild_draw_4': 14}.get(trait, -1)  # Handle invalid trait

        features = np.zeros(19)

        # Only set values if color and trait are valid
        if color_idx != -1:
            features[color_idx] = 1
        if trait_idx != -1:
            features[4 + trait_idx] = 1

        return features

    def state_to_tensor(self, state):
        features = np.zeros(self.state_size)

        # Current card features (19 features)
        current_card = state['target']
        features[:19] = self.card_to_features(current_card)

        # Current color features (4 features)
        color_idx = {'r': 0, 'g': 1, 'b': 2, 'y': 3}[current_card[0]]
        features[19:23] = np.eye(4)[color_idx]

        # Hand cards features (19 features per card)
        for i, card in enumerate(state['hand']):
            start_idx = 23 + (i * 19)  # Start after current card (19) and color (4) features
            end_idx = start_idx + 19
            if end_idx <= len(features):  # Ensure we don't exceed array bounds
                features[start_idx:end_idx] = self.card_to_features(card)

        # Opponent hand sizes (3 features)
        features[-5:-2] = np.array(state['opponent_hand_sizes']) / 7.0

        # Game direction (1 feature)
        features[-2] = state.get('direction', 1)

        # Number of cards in deck (1 feature)
        features[-1] = state.get('deck_size', 0) / 108.0

        return torch.FloatTensor(features)

class UnoEnvironment:
    def __init__(self, num_players=2):
        self.game = UNOGame(num_players)
        self.state_rep = UnoStateRepresentation()
        self.action_space = self.state_rep.action_space

    def reset(self):
        self.game = UNOGame()
        state, _ = self.game.init_game()
        return state

    def step(self, action, return_drawn_card=False):
        state, current_player = self.game.step(action, return_drawn_card)
        done = self.game.game_over()

        # Calculate reward
        reward = self._calculate_reward(done)

        return state, reward, done, current_player

    def _calculate_reward(self, done):
        if done:
            winner = self.game.get_winner()
            if winner.name == "You":
                return 1.0  # Win
            return -1.0  # Lose

        # Intermediate rewards
        reward = 0.0

        # Reward for playing action cards
        if self.game.discard_pile[-1].type == "action":
            reward += 0.2

        return reward