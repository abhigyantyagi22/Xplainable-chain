<div align="center">

#  XAI-Chain

### Explainable AI for Blockchain Security

**Detect malicious blockchain transactions with AI • Explain every decision • Verify on-chain**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Next.js](https://img.shields.io/badge/Next.js-14-black)](https://nextjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110-009688)](https://fastapi.tiangolo.com/)
[![Solidity](https://img.shields.io/badge/Solidity-0.8.20-363636)](https://soliditylang.org/)

[Live Demo](#) • [Documentation](#) • [Quick Start](#-quick-start)

</div>

---

##  Overview

XAI-Chain is a production-ready Web3 + AI security platform that combines machine learning with explainable AI (XAI) to detect malicious blockchain transactions. Every prediction is explained using SHAP values and stored immutably on Polygon Amoy testnet.

###  Key Features

-  **AI-Powered Detection**: XGBoost model trained on blockchain transaction patterns
-  **Explainable AI**: SHAP (SHapley Additive exPlanations) for transparency

-  **On-Chain Verification**: Immutable storage on Polygon Mumbai testnet-  **On-Chain Verification**: Immutable storage on Polygon Mumbai testnet

-  **IPFS Storage**: Decentralized explanation data via Pinata-  **IPFS Storage**: Decentralized explanation data via Pinata

-  **Modern UI**: Next.js 14 with Tailwind CSS and shadcn/ui-  **Modern UI**: Next.js 14 with Tailwind CSS and shadcn/ui

-  **Web3 Integration**: RainbowKit + Wagmi for seamless wallet connection-  **Web3 Integration**: RainbowKit + Wagmi for seamless wallet connection

-  **Real-Time Analysis**: Instant transaction risk assessment-  **Real-Time Analysis**: Instant transaction risk assessment

-  **Interactive Dashboard**: Monitor and track analysis history-  **Interactive Dashboard**: Monitor and track analysis history



------



##  Architecture##  Architecture



``````

┌─────────────────┐       ┌──────────────────┐       ┌─────────────────┐┌─────────────────┐       ┌──────────────────┐       ┌─────────────────┐

│   Frontend      │       │   Backend API    │       │   Blockchain    ││   Frontend      │       │   Backend API    │       │   Blockchain    │

│   (Next.js 14)  │◄─────►│   (FastAPI)      │◄─────►│   (Polygon)     ││   (Next.js 14)  │◄─────►│   (FastAPI)      │◄─────►│   (Polygon)     │

│   + RainbowKit  │       │   + ML Models    │       │   + Smart       ││   + RainbowKit  │       │   + ML Models    │       │   + Smart       │

│                 │       │   + SHAP         │       │     Contract    ││                 │       │   + SHAP         │       │     Contract    │

└─────────────────┘       └──────────────────┘       └─────────────────┘└─────────────────┘       └──────────────────┘       └─────────────────┘

                                   │                                   │

                                   ▼                                   ▼

                          ┌──────────────────┐                          ┌──────────────────┐

                          │   IPFS (Pinata)  │                          │   IPFS (Pinata)  │

                          │   Storage        │                          │   Storage        │

                          └──────────────────┘                          └──────────────────┘

``````



### Data Flow### Data Flow



1. **User submits transaction hash** via frontend1. **User submits transaction hash** via frontend

2. **Backend fetches transaction data** from blockchain2. **Backend fetches transaction data** from blockchain

3. **Features are extracted** (gas price, value, sender history, etc.)3. **Features are extracted** (gas price, value, sender history, etc.)

4. **XGBoost model predicts** if transaction is malicious4. **XGBoost model predicts** if transaction is malicious

5. **SHAP generates explanation** showing feature importance5. **SHAP generates explanation** showing feature importance

6. **Explanation uploaded to IPFS** via Pinata6. **Explanation uploaded to IPFS** via Pinata

7. **Smart contract stores** IPFS hash + risk score on-chain7. **Smart contract stores** IPFS hash + risk score on-chain

8. **Frontend displays** prediction, explanation, and verification links8. **Frontend displays** prediction, explanation, and verification links



------



##  Project Structure##  Project Structure



``````

xai-chain/xai-chain/

├── frontend/                  # Next.js 14 frontend├── frontend/                  # Next.js 14 frontend

│   ├── app/                   # App router pages│   ├── app/                   # App router pages

│   │   ├── page.tsx           # Landing page│   │   ├── page.tsx           # Landing page

│   │   ├── analyze/           # Transaction analysis│   │   ├── analyze/           # Transaction analysis

│   │   └── dashboard/         # Analytics dashboard│   │   └── dashboard/         # Analytics dashboard

│   ├── components/            # React components│   ├── components/            # React components

│   ├── config/                # Wagmi & Web3 configuration│   ├── config/                # Wagmi & Web3 configuration

│   └── public/                # Static assets & ABIs│   └── public/                # Static assets & ABIs

││

├── backend/                   # FastAPI backend├── backend/                   # FastAPI backend

│   ├── app/│   ├── app/

│   │   ├── main.py            # API entry point│   │   ├── main.py            # API entry point

│   │   ├── routers/           # API endpoints│   │   ├── routers/           # API endpoints

│   │   ├── models/            # AI models & Pydantic schemas│   │   ├── models/            # AI models & Pydantic schemas

│   │   ├── services/          # Blockchain & IPFS services│   │   ├── services/          # Blockchain & IPFS services

│   │   └── utils/             # Feature engineering helpers│   │   └── utils/             # Feature engineering helpers

│   ├── data/                  # Training data & scripts│   ├── data/                  # Training data & scripts

│   └── requirements.txt       # Python dependencies│   └── requirements.txt       # Python dependencies

││

├── blockchain/                # Smart contracts & Hardhat├── blockchain/                # Smart contracts & Hardhat

│   ├── contracts/             # Solidity files│   ├── contracts/             # Solidity files

│   ├── scripts/               # Deployment scripts│   ├── scripts/               # Deployment scripts

│   ├── test/                  # Contract tests│   ├── test/                  # Contract tests

│   └── hardhat.config.js      # Hardhat configuration│   └── hardhat.config.js      # Hardhat configuration

││

└── data/                      # Data generation & models└── data/                      # Data generation & models

    ├── generate_sample_data.py    ├── generate_sample_data.py

    └── processed/             # Training datasets    └── processed/             # Training datasets

``````



------



##  Quick Start##  Quick Start



### Prerequisites##  Quick Start



- **Node.js** 20+ and npm### Prerequisites

- **Python** 3.10+ and pip

- **MetaMask** wallet extension### Prerequisites

- **API Keys**: Infura, Pinata, WalletConnect, Etherscan

- Python 3.11+

### Installation

- Node.js 16+- **Node.js** 20+ and npm

#### 1. Clone Repository

- WSL2 (for Windows)- **Python** 3.10+ and pip

```bash

git clone https://github.com/yasharyas/Xplainable-chain.git- **MetaMask** wallet extension

cd Xplainable-chain

```### 1. Backend Setup- **API Keys** (see Setup section)



#### 2. Blockchain Setup



```bash```powershell### Installation

cd blockchain

npm installcd backend



# Copy and configure environment#### 1. Clone Repository

cp .env.example .env

# Edit with: POLYGON_MUMBAI_RPC, PRIVATE_KEY# create virtual environment



# Get Mumbai MATIC: https://mumbaifaucet.com/python -m venv venv```powershell



# Compile and testgit clone https://github.com/yourusername/xai-chain.git

npx hardhat compile

npx hardhat test  # Should pass 6/6 tests# activate itcd xai-chain



# Deploy to Mumbai.\venv\Scripts\Activate.ps1```

npx hardhat run scripts/deploy.js --network mumbai

# Save the contract address!

```

# install packages#### 2. Blockchain Setup

#### 3. Backend Setup

pip install -r requirements.txt

```bash

cd ../backend```powershell

python -m venv venv

.\venv\Scripts\activate  # Windows# generate training data# Navigate to blockchain directory

# source venv/bin/activate  # Linux/Mac

python data/generate_sample_data.pycd blockchain

pip install -r requirements.txt



# Configure environment

cp .env.example .env# train ML model# Install dependencies

# Edit with: CONTRACT_ADDRESS, INFURA_URL, PINATA keys

python train_all_models.pynpm install

# Prepare ML model

python data/generate_sample_data.py```

python train_all_models.py

```# Copy environment file



#### 4. Frontend Setup### 2. Frontend Setupcopy .env.example .env



```bash

cd ../frontend

npm install```powershell# Edit .env with your private key and Infura URL



cp .env.local.example .env.localcd frontend# Get Mumbai MATIC from: https://mumbaifaucet.com/

# Edit with: API_URL, CONTRACT_ADDRESS, WALLETCONNECT_PROJECT_ID

```



### Running the Application# install packages using WSL# Compile contracts



Open **3 terminals**:wsl bash -c "cd /mnt/d/CODING/Xplainable-blockchain/frontend && npm install"npx hardhat compile



**Terminal 1 - Backend:**```

```bash

cd backend# Deploy to Polygon Mumbai

.\venv\Scripts\activate

uvicorn app.main:app --reload### 3. Blockchain Setupnpx hardhat run scripts/deploy.js --network mumbai

# API: http://localhost:8000

``````



**Terminal 2 - Frontend:**```powershell

```bash

cd frontendcd blockchain**Important**: Save the deployed contract address!

npm run dev

# UI: http://localhost:3000

```

# install packages#### 3. Backend Setup

**Terminal 3 - Optional (Local Blockchain):**

```bashwsl bash -c "cd /mnt/d/CODING/Xplainable-blockchain/blockchain && npm install"

cd blockchain

npx hardhat node```powershell

```

# compile contracts# Navigate to backend directory

### Using the Platform

wsl bash -c "cd /mnt/d/CODING/Xplainable-blockchain/blockchain && npx hardhat compile"cd ..\backend

1. Open **http://localhost:3000**

2. **Connect wallet** (MetaMask on Polygon Mumbai)

3. Go to **"Analyze Transaction"**

4. Enter a transaction hash or try this example:# run tests# Create virtual environment

   ```

   0xbf7ba7b25e4fbca4ee0ff460dba1c9ccaf5195e9c2ea24909b0f6e605636ceacwsl bash -c "cd /mnt/d/CODING/Xplainable-blockchain/blockchain && npx hardhat test"python -m venv venv

   ```

5. Click **"Analyze Transaction"**```

6. View **risk assessment** + **SHAP explanation** + **on-chain verification**

# Activate virtual environment

---

## Running the Application.\venv\Scripts\activate

## 📖 API Documentation



Once backend is running:

### Start Backend# Install dependencies

- **Interactive Docs**: http://localhost:8000/docs

- **ReDoc**: http://localhost:8000/redocpip install -r requirements.txt



### Main Endpoints```powershell



#### Analyze Transactioncd d:\CODING\Xplainable-blockchain\backend# Copy environment file

```http

POST /api/analyze$env:PYTHONPATH="d:\CODING\Xplainable-blockchain\backend"copy .env.example .env

Content-Type: application/json

d:\CODING\Xplainable-blockchain\backend\venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

{

  "tx_hash": "0x5c504ed432cb51138bcf09aa5e8a410dd4a1e204ef84bfed1be16dfba1b22060",```# Edit .env with:

  "network": "ethereum"

}# - Contract address from step 2

```

Backend: **http://localhost:8000**# - Infura URL

#### Verify Explanation

```http# - Pinata API keys

GET /api/verify/{tx_hash}

```### Start Frontend# - MongoDB URI



#### Get Audit Trail```

```http

GET /api/audit?limit=10&skip=0```powershell

```

cd d:\CODING\Xplainable-blockchain\frontend#### 4. Generate Sample Data & Train Model

---

wsl bash -c "cd /mnt/d/CODING/Xplainable-blockchain/frontend && npm run dev"

## 🧪 Testing

``````powershell

### Smart Contract Tests

# Generate sample transaction data

```bash

cd blockchainFrontend: **http://localhost:3000**python data\generate_sample_data.py

npx hardhat test

# Expected: 6 passing tests

```

### Start Local Blockchain (Optional)# This creates data/processed/features.csv with 10,000 sample transactions

### Backend Tests

```

```bash

cd backend```powershell

pytest tests/

```cd d:\CODING\Xplainable-blockchain\blockchain**Train the ML model:**



---wsl bash -c "cd /mnt/d/CODING/Xplainable-blockchain/blockchain && npx hardhat node"



## ML Model Details

### Features (9 total)

| # | Feature | Description |
|---|---|---|
| 1 | `amount` | Average ETH value sent per transaction |
| 2 | `gas_price` | Gas price in Gwei (activity-based estimate) |
| 3 | `gas_used` | Gas consumed (estimated from account type) |
| 4 | `gas_price_deviation` | Deviation from network median gas price |
| 5 | `value` | Total ETH sent by account |
| 6 | `sender_tx_count` | Total confirmed outgoing transactions |
| 7 | `is_contract_creation` | 1 if account deployed contracts, else 0 |
| 8 | `contract_age` | Days since contract deployment (0 for EOAs) |
| 9 | `block_gas_used_ratio` | Block gas utilisation ratio (0–1) |

> At inference time, `sender_tx_count`, `contract_age`, `block_gas_used_ratio`,
> and `gas_price_deviation` are enriched with real values from the Etherscan API,
> replacing the training-time estimates.

### Model Card

| Property | Value |
|---|---|
| Algorithm | XGBoost (n\_estimators=300, max\_depth=6, learning\_rate=0.05) |
| Training data | Kaggle Ethereum Fraud Detection Dataset (~9,800 accounts) |
| Class imbalance | Handled via `scale_pos_weight` |
| Test ROC-AUC | ~0.95 |
| Test PR-AUC | reported per run (more informative for imbalanced data) |
| Explainability | SHAP TreeExplainer (per-feature attribution) |

**Known limitations**
- Training data is account-level; real fraud detection needs transaction-level data
- Features at training time are Kaggle proxies; Etherscan enrichment improves inference
- Model should be retrained on Etherscan-enriched transaction-level data when available

### Retraining the Model

```bash
cd backend
python train_all_models.py
```

This trains both `model.pkl` (analysis) and `prevention_model.pkl` (pre-tx check)
from the same canonical feature mapping and saves them to `app/ml/`.

---

# database optionalfeature_columns = [

## 🔑 Environment Variables

MONGODB_URI=mongodb://localhost:27017/xaichain    'gas_price', 'gas_used', 'value', 'gas_price_deviation',

### Blockchain (.env)

    'sender_tx_count', 'contract_age', 'is_contract_creation',

```env

POLYGON_MUMBAI_RPC=https://polygon-mumbai.infura.io/v3/YOUR_KEY# APIs    'function_signature_hash', 'block_gas_used_ratio'

PRIVATE_KEY=your_private_key_without_0x

POLYGONSCAN_API_KEY=your_polygonscan_keyETHERSCAN_API_KEY=your_key]

```

```

### Backend (.env)

X = df[feature_columns]

```env

INFURA_URL=https://polygon-mumbai.infura.io/v3/YOUR_KEY### Frontend (.env.local)y = df['is_malicious']

PRIVATE_KEY=your_private_key_without_0x

CONTRACT_ADDRESS=0x_deployed_contract_address

PINATA_API_KEY=your_pinata_key

PINATA_API_SECRET=your_pinata_secret```env# Split data

MONGODB_URI=mongodb://localhost:27017/xaichain

ETHERSCAN_API_KEY=your_etherscan_keyNEXT_PUBLIC_WALLETCONNECT_PROJECT_ID=your_idX_train, X_test, y_train, y_test = train_test_split(

```

NEXT_PUBLIC_INFURA_API_KEY=your_key    X, y, test_size=0.2, random_state=42, stratify=y

### Frontend (.env.local)

NEXT_PUBLIC_API_URL=http://localhost:8000)

```env

NEXT_PUBLIC_API_URL=http://localhost:8000```

NEXT_PUBLIC_CONTRACT_ADDRESS=0x_deployed_contract_address

NEXT_PUBLIC_WALLETCONNECT_PROJECT_ID=your_walletconnect_id# Scale features

```

## Deploy Smart Contractscaler = StandardScaler()

---

X_train_scaled = scaler.fit_transform(X_train)

## 🛠️ Tech Stack

### Local DeploymentX_test_scaled = scaler.transform(X_test)

| Layer | Technology |

|-------|-----------|

| **Frontend** | Next.js 14, TypeScript, Tailwind CSS, shadcn/ui |

| **Web3** | ethers.js v6, Wagmi v2, RainbowKit |Terminal 1 - Start node:# Train XGBoost

| **Backend** | FastAPI, Uvicorn, Python 3.10+ |

| **AI/ML** | XGBoost, SHAP, scikit-learn, pandas, numpy |```powershellmodel = xgb.XGBClassifier(

| **Blockchain** | Solidity 0.8.20, Hardhat, Polygon Mumbai |

| **Storage** | IPFS (Pinata), MongoDB |cd blockchain    n_estimators=100,

| **APIs** | Web3.py, Infura, Etherscan |

wsl bash -c "cd /mnt/d/CODING/Xplainable-blockchain/blockchain && npx hardhat node"    max_depth=6,

---

```    learning_rate=0.1,

##  Troubleshooting

    random_state=42

### Frontend Chunk Error

Terminal 2 - Deploy:)

```bash

cd frontend```powershellmodel.fit(X_train_scaled, y_train)

rm -rf .next

npm run devcd blockchain

```

wsl bash -c "cd /mnt/d/CODING/Xplainable-blockchain/blockchain && npx hardhat run scripts/deploy.js --network localhost"# Evaluate

### Backend Module Not Found

```y_pred = model.predict(X_test_scaled)

```bash

# Windowsprint(classification_report(y_test, y_pred))

$env:PYTHONPATH="D:\path\to\backend"

python -m uvicorn app.main:app --reloadCopy the address and update `backend/.env`:



# Linux/Mac# Save model and scaler

export PYTHONPATH="/path/to/backend"

python -m uvicorn app.main:app --reload```envwith open('app/ml/model.pkl', 'wb') as f:

```

INFURA_URL=http://127.0.0.1:8545    pickle.dump(model, f)

### Port Already in Use

CONTRACT_ADDRESS=0x5FbDB2315678afecb367f032d93F642f64180aa3with open('app/ml/scaler.pkl', 'wb') as f:

```bash

# Windows - Stop processesPRIVATE_KEY=0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80    pickle.dump(scaler, f)

Get-Process python | Where-Object {$_.CommandLine -like "*uvicorn*"} | Stop-Process -Force

Get-Process node | Stop-Process -Force```



# Linux/Macprint(" Model saved!")

lsof -ti:8000 | xargs kill -9

lsof -ti:3000 | xargs kill -9Restart backend to use real blockchain.```

```



### Contract Deployment Failed

## Using the Platform#### 5. Frontend Setup

- Ensure you have Mumbai MATIC: https://mumbaifaucet.com/

- Check your `PRIVATE_KEY` and `POLYGON_MUMBAI_RPC` in `.env`

- Verify Infura API key is valid

1. Open http://localhost:3000```powershell

---

2. Connect wallet (MetaMask, Rainbow, etc)# Navigate to frontend directory

## 🤝 Contributing

3. Go to "Analyze Transaction"cd ..\frontend

Contributions are welcome! Please follow these steps:

4. Enter transaction hash

1. Fork the repository

2. Create your feature branch (`git checkout -b feature/AmazingFeature`)5. Click "Analyze Transaction"# Install dependencies

3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)

4. Push to the branch (`git push origin feature/AmazingFeature`)6. View risk analysisnpm install

5. Open a Pull Request



---

## API Endpoints# Copy environment file

## 📄 License

copy .env.local.example .env.local

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

**Health Check**

---

```# Edit .env.local with:

## 🙏 Acknowledgments

GET http://localhost:8000/# - API URL (http://localhost:8000)

- **SHAP**: For explainable AI framework

- **Hardhat**: For Ethereum development environment```# - Contract address

- **RainbowKit**: For beautiful wallet connection UI

- **shadcn/ui**: For modern UI components# - WalletConnect Project ID (get from https://cloud.walletconnect.com)

- **Pinata**: For IPFS pinning service

**Analyze Transaction**```

---

```

## 🗺️ Roadmap

POST http://localhost:8000/api/analyze/### Running the Application

- [ ] Support for multiple blockchains (Ethereum, BSC, Avalanche)

- [ ] Real-time monitoring dashboard```

- [ ] Batch transaction analysis

- [ ] Advanced XAI visualizations (LIME, counterfactuals)Open **3 terminal windows**:

- [ ] Mobile app (React Native)

- [ ] Historical analytics and trendsRequest:

- [ ] API rate limiting and authentication

- [ ] Mainnet deployment```json**Terminal 1 - Backend:**



---{```powershell



<div align="center">  "tx_hash": "0xbf7ba7b25e4fbca4ee0ff460dba1c9ccaf5195e9c2ea24909b0f6e605636ceac",cd backend



**Built with ❤️ for the Web3 community**  "network": "ethereum",.\venv\Scripts\activate



[GitHub](https://github.com/yasharyas/Xplainable-chain) • [Documentation](#) • [Issues](https://github.com/yasharyas/Xplainable-chain/issues)  "transaction_data": {uvicorn app.main:app --reload



</div>    "amount": 0.01040272,```


    "gas_price": 0.117164461,API will run at: http://localhost:8000

    "gas_used": 21000,

    "num_transfers": 1,**Terminal 2 - Frontend:**

    "unique_addresses": 2,```powershell

    "time_of_day": 10,cd frontend

    "contract_interaction": 0,npm run dev

    "sender_tx_count": 150,```

    "receiver_tx_count": 75Frontend will run at: http://localhost:3000

  }

}**Terminal 3 - Optional monitoring:**

``````powershell

# View logs, check contracts, etc.

**Get Audit Trail**```

```

GET http://localhost:8000/api/audit/### Access the Application

```

1. Open browser to http://localhost:3000

**Verify Transaction**2. Connect your MetaMask wallet (switch to Polygon Mumbai)

```3. Click "Analyze Transaction"

GET http://localhost:8000/api/verify/{tx_hash}4. Enter a transaction hash

```5. View AI prediction + SHAP explanation + on-chain verification!



## 📖 API Documentation

Once the backend is running, visit:
- **Interactive Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Main Endpoints

#### Analyze Transaction
```http
POST /api/analyze
Content-Type: application/json

{
  "tx_hash": "0x5c504ed432cb51138bcf09aa5e8a410dd4a1e204ef84bfed1be16dfba1b22060",
  "network": "ethereum"
}
```

#### Verify Explanation
```http
GET /api/verify/{tx_hash}
```

#### Get Audit Trail
```http
GET /api/audit?limit=10&skip=0
```



## Troubleshooting## 🧪 Testing



### Frontend Chunk Error### Smart Contract Tests



```powershell```powershell

cd frontendcd blockchain

Remove-Item -Recurse -Force .nextnpx hardhat test

wsl bash -c "cd /mnt/d/CODING/Xplainable-blockchain/frontend && npm run dev"```

```

### Backend Tests

### Backend Module Not Found

```powershell

```powershellcd backend

cd backendpytest tests/

$env:PYTHONPATH="d:\CODING\Xplainable-blockchain\backend"```

d:\CODING\Xplainable-blockchain\backend\venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

```##  Project Structure



### Port Already in Use```

xai-chain/

Stop processes:├── frontend/                  # Next.js 14 frontend

```powershell│   ├── app/                  # App router pages

# stop backend│   ├── components/           # React components

Get-Process python | Where-Object {$_.CommandLine -like "*uvicorn*"} | Stop-Process -Force│   ├── config/               # Wagmi configuration

│   └── lib/                  # Utilities

# stop frontend│

Get-Process | Where-Object {$_.ProcessName -eq "node"} | Stop-Process -Force├── backend/                  # FastAPI backend

```│   ├── app/

│   │   ├── main.py          # Entry point

### WSL Issues│   │   ├── routers/         # API endpoints

│   │   ├── models/          # AI models & schemas

```powershell│   │   ├── services/        # Blockchain & IPFS

wsl --shutdown│   │   └── utils/           # Helpers

```│   └── requirements.txt

│

Wait 10 seconds and retry.├── blockchain/               # Smart contracts

│   ├── contracts/           # Solidity files

## Contract Tests│   ├── scripts/             # Deployment scripts

│   ├── test/                # Contract tests

```powershell│   └── hardhat.config.js

cd blockchain│

wsl bash -c "cd /mnt/d/CODING/Xplainable-blockchain/blockchain && npx hardhat test"└── data/                    # Data & models

```    ├── generate_sample_data.py

    └── processed/           # Training data

All 6 tests should pass.```



## Architecture## 🔑 Environment Variables



### Data Flow### Blockchain (.env)

```env

1. User submits transaction hashPOLYGON_MUMBAI_RPC=https://polygon-mumbai.infura.io/v3/YOUR_KEY

2. Frontend sends request to backendPRIVATE_KEY=your_private_key_without_0x

3. Backend extracts 9 featuresPOLYGONSCAN_API_KEY=your_polygonscan_key

4. XGBoost model predicts risk```

5. SHAP generates explanation

6. Result stored on IPFS### Backend (.env)

7. Result stored on blockchain (optional)```env

8. Frontend displays analysisINFURA_URL=https://polygon-mumbai.infura.io/v3/YOUR_KEY

PRIVATE_KEY=your_private_key_without_0x

### SecurityCONTRACT_ADDRESS=0x_deployed_contract_address

PINATA_API_KEY=your_pinata_key

- Private keys not in frontendPINATA_API_SECRET=your_pinata_secret

- API rate limitingMONGODB_URI=mongodb://localhost:27017/xaichain

- Smart contracts testedETHERSCAN_API_KEY=your_etherscan_key

- IPFS content addressed```

- Blockchain immutability

### Frontend (.env.local)

## Current Status```env

NEXT_PUBLIC_API_URL=http://localhost:8000

- ML Model: TrainedNEXT_PUBLIC_CONTRACT_ADDRESS=0x_deployed_contract_address

- Backend API: WorkingNEXT_PUBLIC_WALLETCONNECT_PROJECT_ID=your_walletconnect_id

- Frontend UI: 3 pages complete```

- Smart Contracts: Compiled and tested

- Blockchain: Configurable (mocked by default)## 🎓 How It Works

- IPFS: Configurable (mocked by default)

1. **User submits transaction hash** via frontend

## Example Transaction2. **Backend fetches transaction data** from blockchain

3. **Features are extracted** (gas price, value, sender history, etc.)

Try this real Ethereum transaction:4. **XGBoost model predicts** if transaction is malicious

```5. **SHAP generates explanation** showing feature importance

0xbf7ba7b25e4fbca4ee0ff460dba1c9ccaf5195e9c2ea24909b0f6e605636ceac6. **Explanation uploaded to IPFS** via Pinata

```7. **Smart contract stores** IPFS hash + risk score on-chain

8. **Frontend displays** prediction, explanation, and verification links

Details:

- From: buildernet.eth## 🛠️ Tech Stack

- To: 0x3cEFB98AbB3ebf3AFAFF3A377285fe6d4eA3907e

- Value: 0.01040272 ETH| Layer | Technology |

- Gas Price: 0.117164461 Gwei|-------|-----------|

- Block: 23696643| Frontend | Next.js 14, TypeScript, Tailwind CSS, shadcn/ui |

| Web3 | ethers.js v6, Wagmi v2, RainbowKit |

## License| Backend | FastAPI, Uvicorn, Python 3.10+ |

| AI/ML | XGBoost, SHAP, scikit-learn, pandas, numpy |

MIT| Blockchain | Solidity 0.8.20, Hardhat, Polygon Mumbai |

| Storage | IPFS (Pinata), MongoDB |

---| APIs | Web3.py, Infura, Etherscan |



Built for blockchain security with explainable AI.## 🤝 Contributing


Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **SHAP**: For explainable AI framework
- **Hardhat**: For Ethereum development environment
- **RainbowKit**: For beautiful wallet connection UI
- **shadcn/ui**: For beautiful UI components
- **Pinata**: For IPFS pinning service

## 📞 Support

- **Documentation**: [https://xai-chain-docs.vercel.app](https://xai-chain-docs.vercel.app)
- **Issues**: [GitHub Issues](https://github.com/yourusername/xai-chain/issues)
- **Discord**: [Join our community](#)
- **Email**: support@xai-chain.io

## 🗺️ Roadmap

- [ ] Support for multiple blockchains (Ethereum, BSC, etc.)
- [ ] Real-time monitoring dashboard
- [ ] Batch transaction analysis
- [ ] Advanced XAI visualizations (LIME, counterfactuals)
- [ ] Mobile app (React Native)
- [ ] Historical analytics and trends
- [ ] API rate limiting and authentication
- [ ] Mainnet deployment

---

<div align="center">

**Built with ❤️ for the Web3 community**

[Website](#) • [Documentation](#) • [Twitter](#) • [Discord](#)

</div>
