## About The Project

This is an updated version of the terminal text-based game [The Resistance: Coup](https://www.ultraboardgames.com/coup/game-rules.php#google_vignette). It builds upon the original project by [dirkbrnd](https://github.com/dirkbrnd/resistance_coup) and introduces a new level of challenge with AI opponents powered by a Large Language Model (LLM) using LangGraph.

In a nutshell:

* You have some character cards representing government officials you have influence over.
* You can perform actions to sabotage other players and reduce their influence (i.e., remove their cards).
* The last person with any cards left is the winner!

This version now features enhanced AI players driven by an LLM, providing a more dynamic and engaging gaming experience.

## Getting Started

### Prerequisites

* Python 3.12
* Poetry (for dependency management)

### Setting Up the Environment

1. **Clone the repository:**

   ```bash
   git clone https://github.com/cl0ver012/resistance_coup.git
   ```

2. **Install dependencies using Poetry:**

   ```bash
   cd resistance_coup
   poetry install
   ```

## How to Run

1. **Launch the game:**

   ```bash
   python coup.py
   ```

2. **Enter your name when prompted.**

3. **You will see AI players automatically playing game.**

4. **Enjoy the game!**

## LLM Game Player Implementation with LangGraph

This project leverages the power of LangGraph to create intelligent AI opponents that can understand and respond to the game's dynamics. The LLM is used to:

* **Analyze the game state:** The AI assesses the current situation, including the cards in play, the actions taken by other players, and the overall game progress.
* **Make strategic decisions:** Based on its analysis, the AI decides which actions to take, aiming to maximize its chances of winning.
* **Adapt to different players:** The AI can learn from previous games and adjust its strategies based on the behavior of its opponents.

This integration of LLM and LangGraph brings a new dimension to the gameplay, making the AI opponents more challenging and unpredictable.
