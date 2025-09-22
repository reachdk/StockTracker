"""
Improved Stock Tracker with better error handling, logging, and configuration
"""
import glob
import sys
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from pandas.tseries.offsets import BDay
from typing import List, Tuple, Optional, Dict
import os

from config import Config
from logger import setup_logger
from email_service import EmailService


class StockTracker:
    """Main stock tracking class with improved error handling and logging"""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = setup_logger()
        self.email_service = EmailService(config.email, self.logger)
        
        # Ensure data directories exist
        os.makedirs(self.config.tracker.data_dir, exist_ok=True)
        os.makedirs(self.config.tracker.input_dir, exist_ok=True)
    
    def days_between(self, d1: str, d2: str) -> int:
        """Calculate days between two date strings"""
        try:
            date1 = datetime.strptime(d1, "%Y-%m-%d")
            date2 = datetime.strptime(d2, "%Y-%m-%d")
            return abs((date2 - date1).days)
        except ValueError as e:
            self.logger.error(f"Error parsing dates {d1}, {d2}: {e}")
            return 0
    
    def get_investments(self) -> bool:
        """Load and process investment files"""
        try:
            input_pattern = os.path.join(self.config.tracker.input_dir, "*.csv")
            input_files = glob.glob(input_pattern)
            
            if not input_files:
                self.logger.warning(f"No input files found in {self.config.tracker.input_dir}")
                return False
            
            self.logger.info(f"Processing {len(input_files)} investment files")
            
            dataframes = []
            for filename in input_files:
                try:
                    df = pd.read_csv(filename, index_col=None, header=0)
                    dataframes.append(df)
                    self.logger.debug(f"Loaded {filename} with {len(df)} records")
                except Exception as e:
                    self.logger.error(f"Error reading {filename}: {e}")
                    continue
            
            if not dataframes:
                self.logger.error("No valid investment files found")
                return False
            
            # Combine and clean data
            investments = pd.concat(dataframes, axis=0, ignore_index=True)
            
            if 'Symbol' not in investments.columns:
                self.logger.error("Symbol column not found in investment files")
                return False
            
            investments.drop_duplicates(subset='Symbol', keep='first', inplace=True)
            investments.drop(investments.columns[1:], axis=1, inplace=True)
            investments.set_index('Symbol', inplace=True)
            investments.sort_index(inplace=True)
            
            # Save processed investments
            investments.to_csv(self.config.tracker.investments_file)
            self.logger.info(f"Processed {len(investments)} unique symbols")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error in get_investments: {e}")
            return False
    
    def update_meta(self) -> List[str]:
        """Update metadata for investments"""
        try:
            # Load current data
            investments_df = pd.read_csv(self.config.tracker.investments_file, header=0, index_col=0)
            
            # Load or create data file
            if os.path.exists(self.config.tracker.data_file):
                data_df = pd.read_csv(self.config.tracker.data_file, header=0, index_col=0)
            else:
                data_df = pd.DataFrame(columns=['high', 'high_date', 'close', 'tolerance', 'updated'])
            
            deleted_symbols = []
            
            # Add new symbols
            for symbol in investments_df.index:
                if symbol not in data_df.index:
                    data_df.loc[symbol] = [1, '', 1, self.config.tracker.default_tolerance, '']
                    self.logger.info(f"Added new symbol: {symbol}")
            
            # Remove symbols no longer in investments
            for symbol in data_df.index:
                if symbol not in investments_df.index:
                    deleted_symbols.append(symbol)
            
            if deleted_symbols:
                data_df.drop(deleted_symbols, inplace=True)
                self.logger.info(f"Removed symbols: {deleted_symbols}")
            
            # Save updated data
            data_df.sort_index(inplace=True)
            data_df.to_csv(self.config.tracker.data_file)
            
            return deleted_symbols
            
        except Exception as e:
            self.logger.error(f"Error in update_meta: {e}")
            return []
    
    def update_prices(self) -> bool:
        """Update stock prices from Yahoo Finance"""
        try:
            if not os.path.exists(self.config.tracker.data_file):
                self.logger.error(f"Data file not found: {self.config.tracker.data_file}")
                return False
            
            symbol_list = pd.read_csv(self.config.tracker.data_file, index_col='symbol')
            
            if symbol_list.empty:
                self.logger.warning("No symbols to update")
                return True
            
            # Calculate date range
            curr_day = datetime.today()
            prev_day = curr_day - BDay(self.config.tracker.lookback_days)
            
            # Prepare ticker string for yfinance
            ticker_list = symbol_list.index.tolist()
            ticker_string = ' '.join(ticker_list)
            
            self.logger.info(f"Fetching data for {len(ticker_list)} symbols from {prev_day.date()} to {curr_day.date()}")
            
            # Fetch data from Yahoo Finance
            try:
                ticker_hist = yf.download(ticker_string, start=prev_day, end=curr_day, progress=False)
                
                if ticker_hist.empty:
                    self.logger.warning("No data returned from Yahoo Finance")
                    return False
                
                # Handle single vs multiple tickers
                if len(ticker_list) == 1:
                    close_data = {ticker_list[0]: ticker_hist['Close']}
                else:
                    close_data = ticker_hist['Close']
                
            except Exception as e:
                self.logger.error(f"Error fetching data from Yahoo Finance: {e}")
                return False
            
            # Update prices
            updated_count = 0
            for symbol in symbol_list.index:
                try:
                    if symbol in close_data:
                        prices = close_data[symbol].dropna()
                        
                        if not prices.empty:
                            min_close = prices.min()
                            symbol_list.loc[symbol, 'close'] = min_close
                            symbol_list.loc[symbol, 'updated'] = datetime.now().date()
                            
                            # Update high if current minimum is higher than recorded high
                            if min_close > symbol_list.loc[symbol, 'high']:
                                symbol_list.loc[symbol, 'high'] = min_close
                                symbol_list.loc[symbol, 'high_date'] = datetime.now().date()
                                self.logger.info(f"New high for {symbol}: {min_close}")
                            
                            updated_count += 1
                        else:
                            self.logger.warning(f"No valid price data for {symbol}")
                    else:
                        self.logger.warning(f"Symbol {symbol} not found in Yahoo Finance data")
                        
                except Exception as e:
                    self.logger.error(f"Error updating prices for {symbol}: {e}")
                    continue
            
            # Save updated data
            symbol_list.to_csv(self.config.tracker.data_file)
            self.logger.info(f"Updated prices for {updated_count} symbols")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error in update_prices: {e}")
            return False
    
    def calculate_variance(self) -> bool:
        """Calculate variance and send notifications if thresholds are breached"""
        try:
            if not os.path.exists(self.config.tracker.data_file):
                self.logger.error(f"Data file not found: {self.config.tracker.data_file}")
                return False
            
            notify_data = pd.read_csv(self.config.tracker.data_file, header=0, index_col=0)
            
            # Initialize alert categories
            alerts = {
                'tolerance_breach': [],
                'ten_percent': [],
                'five_percent': [],
                'stagnant': []
            }
            
            # Check each stock
            for index, row in notify_data.iterrows():
                try:
                    # Calculate percentage drop from high
                    if pd.isna(row['high']) or pd.isna(row['close']) or row['high'] == 0:
                        continue
                    
                    diff = ((row['high'] - row['close']) / row['high']) * 100
                    
                    # Check stagnation
                    if pd.notna(row['updated']) and pd.notna(row['high_date']):
                        stagnating_days = self.days_between(str(row['updated']), str(row['high_date']))
                        if stagnating_days > self.config.tracker.stagnation_threshold_days:
                            alerts['stagnant'].append([index, stagnating_days])
                    
                    # Check tolerance breach
                    if diff > row['tolerance']:
                        alerts['tolerance_breach'].append([index, round(diff, 2)])
                    
                    # Check percentage thresholds
                    if diff >= 10:
                        alerts['ten_percent'].append([index, round(diff, 2)])
                    elif diff >= 5:
                        alerts['five_percent'].append([index, round(diff, 2)])
                        
                except Exception as e:
                    self.logger.error(f"Error processing {index}: {e}")
                    continue
            
            # Send notifications if needed
            if any(alerts.values()):
                return self._send_alerts(alerts)
            else:
                self.logger.info("No alerts to send")
                return True
                
        except Exception as e:
            self.logger.error(f"Error in calculate_variance: {e}")
            return False
    
    def _send_alerts(self, alerts: Dict[str, List]) -> bool:
        """Send email alerts based on calculated variances"""
        try:
            subject_parts = []
            message_parts = []
            
            # Build message content
            if alerts['tolerance_breach']:
                subject_parts.append("Tolerance Breach")
                message_parts.append("🚨 CONSIDER SELLING - Tolerance Breached:")
                for symbol, diff in alerts['tolerance_breach']:
                    message_parts.append(f"  {symbol}: {diff}% drop from high")
                message_parts.append("")
            
            if alerts['ten_percent']:
                if not subject_parts:
                    subject_parts.append("10% Threshold Breached")
                message_parts.append("⚠️  10% Threshold Breached:")
                for symbol, diff in alerts['ten_percent']:
                    message_parts.append(f"  {symbol}: {diff}% drop from high")
                message_parts.append("")
            
            if alerts['five_percent']:
                if not subject_parts:
                    subject_parts.append("5% Threshold Breached")
                message_parts.append("📉 5% Threshold Breached:")
                for symbol, diff in alerts['five_percent']:
                    message_parts.append(f"  {symbol}: {diff}% drop from high")
                message_parts.append("")
            
            if alerts['stagnant']:
                if not subject_parts:
                    subject_parts.append("Stagnant Stocks")
                message_parts.append("😴 Stagnant Stocks (Time to Review?):")
                for symbol, days in alerts['stagnant']:
                    message_parts.append(f"  {symbol}: {days} days since peak")
                message_parts.append("")
            
            # Create final message
            subject = f"Stock Alert: {', '.join(subject_parts)} - {datetime.now().strftime('%Y-%m-%d')}"
            message = "\n".join(message_parts)
            
            # Send email
            success = self.email_service.send_notification(subject, message)
            
            if success:
                self.logger.info(f"Alert sent successfully: {subject}")
            else:
                self.logger.error("Failed to send alert email")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error sending alerts: {e}")
            return False
    
    def run(self, update_investments: bool = False) -> bool:
        """Main execution method"""
        try:
            self.logger.info("Starting stock tracker run")
            
            # Update investments if requested
            if update_investments:
                self.logger.info("Updating investment list")
                if not self.get_investments():
                    return False
                
                deleted_symbols = self.update_meta()
                if deleted_symbols:
                    self.logger.info(f"Removed {len(deleted_symbols)} symbols from tracking")
            
            # Update prices and calculate alerts
            if not self.update_prices():
                return False
            
            if not self.calculate_variance():
                return False
            
            self.logger.info("Stock tracker run completed successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error in main run: {e}")
            return False


def main():
    """Main entry point"""
    try:
        # Load configuration
        config = Config()
        
        # Validate configuration
        errors = config.validate()
        if errors:
            print("Configuration errors:")
            for error in errors:
                print(f"  - {error}")
            print("\nPlease set the required environment variables and try again.")
            return 1
        
        # Create tracker instance
        tracker = StockTracker(config)
        
        # Check command line arguments
        update_investments = len(sys.argv) > 1 and sys.argv[1] == '--update-investments'
        
        # Run tracker
        success = tracker.run(update_investments=update_investments)
        
        return 0 if success else 1
        
    except Exception as e:
        print(f"Fatal error: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())