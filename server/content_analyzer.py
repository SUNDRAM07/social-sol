"""
Content Analyzer Service
Analyzes uploaded files, URLs, and extracts insights for idea generation
"""

import os
import csv
import json
import requests
import pandas as pd
from typing import Dict, List, Any, Optional
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from PIL import Image
import mimetypes
import io
import base64

class ContentAnalyzer:
    """Analyzes various content types for idea generation"""
    
    def __init__(self):
        self.max_url_content_length = 10000  # Limit scraped content length
        self.supported_image_formats = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
        self.supported_doc_formats = ['.pdf', '.txt', '.md', '.doc', '.docx']
    
    async def analyze_trend_data(self, file_path: str = None, file_content: bytes = None, filename: str = "") -> Dict[str, Any]:
        """
        Analyze trend data from CSV files or other formats
        """
        try:
            trends_analysis = {
                "trending_topics": [],
                "top_keywords": [],
                "engagement_metrics": {},
                "time_patterns": {},
                "content_themes": [],
                "analysis_summary": ""
            }
            
            # Handle CSV files
            if filename.lower().endswith('.csv') or (file_path and file_path.lower().endswith('.csv')):
                df = None
                if file_content:
                    df = pd.read_csv(io.BytesIO(file_content))
                elif file_path:
                    df = pd.read_csv(file_path)
                
                if df is not None:
                    # Extract trending topics from CSV
                    topic_columns = [col for col in df.columns if any(keyword in col.lower() 
                                   for keyword in ['topic', 'trend', 'hashtag', 'keyword', 'title', 'subject'])]
                    
                    engagement_columns = [col for col in df.columns if any(keyword in col.lower() 
                                        for keyword in ['like', 'share', 'comment', 'engagement', 'view', 'reach'])]
                    
                    # Extract top trending topics
                    for col in topic_columns[:3]:  # Limit to first 3 topic columns
                        if col in df.columns:
                            top_topics = df[col].value_counts().head(10).index.tolist()
                            trends_analysis["trending_topics"].extend([str(topic) for topic in top_topics if pd.notna(topic)])
                    
                    # Extract engagement insights
                    for col in engagement_columns[:2]:  # Limit to first 2 engagement columns
                        if col in df.columns and df[col].dtype in ['int64', 'float64']:
                            trends_analysis["engagement_metrics"][col] = {
                                "average": float(df[col].mean()) if not df[col].empty else 0,
                                "max": float(df[col].max()) if not df[col].empty else 0,
                                "trend": "increasing" if df[col].is_monotonic_increasing else "mixed"
                            }
                    
                    # Generate analysis summary
                    trends_analysis["analysis_summary"] = f"Analyzed {len(df)} trend records. "
                    if trends_analysis["trending_topics"]:
                        trends_analysis["analysis_summary"] += f"Top trending themes: {', '.join(trends_analysis['trending_topics'][:5])}. "
                    
                    trends_analysis["analysis_summary"] += f"Data shows engagement patterns across {len(engagement_columns)} metrics."
                    
            return trends_analysis
            
        except Exception as e:
            print(f"❌ Error analyzing trend data: {str(e)}")
            return {
                "trending_topics": [],
                "analysis_summary": f"Failed to analyze trend data: {str(e)}",
                "error": str(e)
            }
    
    async def analyze_url_content(self, url: str, analysis_type: str = "general") -> Dict[str, Any]:
        """
        Scrape and analyze content from URLs (brand assets, competitor sites)
        """
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract basic content
            title = soup.find('title')
            title_text = title.get_text().strip() if title else ""
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Extract text content
            text_content = soup.get_text()
            # Clean up text
            lines = (line.strip() for line in text_content.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            clean_text = ' '.join(chunk for chunk in chunks if chunk)
            
            # Limit content length
            if len(clean_text) > self.max_url_content_length:
                clean_text = clean_text[:self.max_url_content_length] + "..."
            
            # Extract meta information
            meta_description = ""
            meta_desc_tag = soup.find('meta', attrs={'name': 'description'})
            if meta_desc_tag:
                meta_description = meta_desc_tag.get('content', '')
            
            # Extract keywords
            meta_keywords = ""
            meta_keywords_tag = soup.find('meta', attrs={'name': 'keywords'})
            if meta_keywords_tag:
                meta_keywords = meta_keywords_tag.get('content', '')
            
            # Extract headings for structure
            headings = []
            for i in range(1, 4):  # h1, h2, h3
                for heading in soup.find_all(f'h{i}'):
                    headings.append(heading.get_text().strip())
            
            analysis_result = {
                "url": url,
                "title": title_text,
                "meta_description": meta_description,
                "meta_keywords": meta_keywords,
                "headings": headings[:10],  # Limit to first 10 headings
                "content_preview": clean_text[:500] + "..." if len(clean_text) > 500 else clean_text,
                "full_content": clean_text,
                "content_length": len(clean_text),
                "analysis_type": analysis_type,
                "scraped_at": pd.Timestamp.now().isoformat()
            }
            
            # Add specific analysis based on type
            if analysis_type == "brand":
                analysis_result["brand_analysis"] = self._analyze_brand_content(clean_text, title_text, headings)
            elif analysis_type == "competitor":
                analysis_result["competitor_analysis"] = self._analyze_competitor_content(clean_text, title_text, headings)
            
            return analysis_result
            
        except Exception as e:
            print(f"❌ Error analyzing URL {url}: {str(e)}")
            return {
                "url": url,
                "error": str(e),
                "analysis_summary": f"Failed to analyze URL: {str(e)}",
                "analysis_type": analysis_type
            }
    
    def _analyze_brand_content(self, content: str, title: str, headings: List[str]) -> Dict[str, Any]:
        """Extract brand-specific insights from content"""
        content_lower = content.lower()
        
        # Common brand elements to look for
        brand_indicators = {
            "services": ["service", "solution", "platform", "api", "software", "technology", "product"],
            "values": ["mission", "vision", "value", "commitment", "believe", "dedicated"],
            "industries": ["enterprise", "business", "corporate", "industry", "sector"],
            "technologies": ["ai", "cloud", "digital", "automation", "analytics", "data"],
            "achievements": ["award", "certification", "client", "customer", "success", "leader"]
        }
        
        brand_analysis = {}
        for category, keywords in brand_indicators.items():
            matches = [keyword for keyword in keywords if keyword in content_lower]
            if matches:
                brand_analysis[category] = matches
        
        # Extract potential brand messaging
        sentences = content.split('.')
        brand_messaging = []
        for sentence in sentences[:20]:  # First 20 sentences
            sentence = sentence.strip()
            if any(keyword in sentence.lower() for keyword in ["we", "our", "provide", "offer", "help", "enable"]):
                if len(sentence) > 20 and len(sentence) < 200:  # Reasonable length
                    brand_messaging.append(sentence)
        
        return {
            "brand_elements": brand_analysis,
            "key_messaging": brand_messaging[:5],  # Top 5 messages
            "content_themes": list(brand_analysis.keys()),
            "analysis_summary": f"Identified {len(brand_analysis)} brand element categories and {len(brand_messaging)} key messages"
        }
    
    def _analyze_competitor_content(self, content: str, title: str, headings: List[str]) -> Dict[str, Any]:
        """Extract competitor-specific insights from content"""
        content_lower = content.lower()
        
        # Extract competitive elements
        competitive_elements = {
            "strategies": ["strategy", "approach", "methodology", "framework"],
            "offerings": ["product", "service", "solution", "feature", "benefit"],
            "positioning": ["leader", "best", "top", "first", "pioneer", "innovative"],
            "target_markets": ["enterprise", "small business", "startup", "industry", "sector"],
            "pain_points": ["challenge", "problem", "issue", "difficulty", "struggle"]
        }
        
        competitor_analysis = {}
        for category, keywords in competitive_elements.items():
            matches = [keyword for keyword in keywords if keyword in content_lower]
            if matches:
                competitor_analysis[category] = matches
        
        return {
            "competitive_elements": competitor_analysis,
            "content_structure": headings[:5],  # Top 5 headings
            "differentiation_opportunities": self._identify_gaps(competitor_analysis),
            "analysis_summary": f"Analyzed competitor positioning across {len(competitor_analysis)} dimensions"
        }
    
    def _identify_gaps(self, competitor_analysis: Dict[str, List[str]]) -> List[str]:
        """Identify potential differentiation opportunities"""
        gaps = []
        
        # This is a simplified gap analysis - in practice, this would be more sophisticated
        if "strategies" not in competitor_analysis:
            gaps.append("Limited strategic messaging - opportunity to highlight unique approach")
        
        if "innovation" not in str(competitor_analysis).lower():
            gaps.append("Innovation positioning opportunity")
        
        if "customer" not in str(competitor_analysis).lower():
            gaps.append("Customer-centric messaging opportunity")
        
        return gaps[:3]  # Top 3 opportunities
    
    async def analyze_uploaded_file(self, file_path: str, filename: str, file_type: str) -> Dict[str, Any]:
        """
        Analyze uploaded files (images, documents, etc.)
        """
        try:
            file_extension = os.path.splitext(filename)[1].lower()
            analysis_result = {
                "filename": filename,
                "file_type": file_type,
                "file_extension": file_extension,
                "analysis_summary": ""
            }
            
            # Handle different file types
            if file_extension in self.supported_image_formats:
                # Analyze images
                with Image.open(file_path) as img:
                    analysis_result.update({
                        "image_analysis": {
                            "dimensions": img.size,
                            "format": img.format,
                            "mode": img.mode,
                            "colors": len(img.getcolors()) if img.getcolors() else "many"
                        },
                        "analysis_summary": f"Image analysis: {img.size[0]}x{img.size[1]} {img.format} image with {img.mode} color mode"
                    })
            
            elif file_extension == '.csv':
                # CSV files - use trend analysis
                with open(file_path, 'rb') as f:
                    content = f.read()
                trend_analysis = await self.analyze_trend_data(file_content=content, filename=filename)
                analysis_result.update(trend_analysis)
            
            elif file_extension == '.txt' or file_extension == '.md':
                # Text files
                with open(file_path, 'r', encoding='utf-8') as f:
                    text_content = f.read()
                
                analysis_result.update({
                    "text_analysis": {
                        "word_count": len(text_content.split()),
                        "line_count": len(text_content.splitlines()),
                        "content_preview": text_content[:300] + "..." if len(text_content) > 300 else text_content
                    },
                    "analysis_summary": f"Text analysis: {len(text_content.split())} words, {len(text_content.splitlines())} lines"
                })
            
            return analysis_result
            
        except Exception as e:
            print(f"❌ Error analyzing uploaded file {filename}: {str(e)}")
            return {
                "filename": filename,
                "error": str(e),
                "analysis_summary": f"Failed to analyze file: {str(e)}"
            }
    
    async def comprehensive_analysis(self, user_data: Dict[str, Any], uploaded_files: List[Dict] = None) -> Dict[str, Any]:
        """
        Perform comprehensive analysis of all provided content
        """
        analysis_results = {
            "brand_insights": {},
            "competitor_insights": {},
            "trend_insights": {},
            "file_insights": [],
            "comprehensive_summary": "",
            "key_recommendations": []
        }
        
        try:
            # Analyze brand assets URLs
            brand_assets_urls = user_data.get('brand_assets_urls', '')
            if brand_assets_urls:
                urls = [url.strip() for url in brand_assets_urls.split('\n') if url.strip()]
                for url in urls[:3]:  # Limit to 3 URLs to avoid timeouts
                    brand_analysis = await self.analyze_url_content(url, "brand")
                    analysis_results["brand_insights"][url] = brand_analysis
            
            # Analyze competitor URLs
            competitor_urls = user_data.get('competitor_urls', '')
            if competitor_urls:
                urls = [url.strip() for url in competitor_urls.split('\n') if url.strip()]
                for url in urls[:3]:  # Limit to 3 URLs
                    competitor_analysis = await self.analyze_url_content(url, "competitor")
                    analysis_results["competitor_insights"][url] = competitor_analysis
            
            # Analyze uploaded files (if provided)
            if uploaded_files:
                for file_info in uploaded_files[:5]:  # Limit to 5 files
                    file_analysis = await self.analyze_uploaded_file(
                        file_info['path'], 
                        file_info['filename'], 
                        file_info.get('type', 'unknown')
                    )
                    analysis_results["file_insights"].append(file_analysis)
            
            # Generate comprehensive summary
            summary_parts = []
            if analysis_results["brand_insights"]:
                summary_parts.append(f"Analyzed {len(analysis_results['brand_insights'])} brand sources")
            if analysis_results["competitor_insights"]:
                summary_parts.append(f"analyzed {len(analysis_results['competitor_insights'])} competitor sources")
            if analysis_results["file_insights"]:
                summary_parts.append(f"processed {len(analysis_results['file_insights'])} uploaded files")
            
            analysis_results["comprehensive_summary"] = "Content analysis complete: " + ", ".join(summary_parts)
            
            # Generate recommendations
            analysis_results["key_recommendations"] = self._generate_content_recommendations(analysis_results)
            
            return analysis_results
            
        except Exception as e:
            print(f"❌ Error in comprehensive analysis: {str(e)}")
            return {
                "error": str(e),
                "comprehensive_summary": f"Analysis failed: {str(e)}",
                "key_recommendations": []
            }
    
    def _generate_content_recommendations(self, analysis_results: Dict[str, Any]) -> List[str]:
        """Generate content recommendations based on analysis"""
        recommendations = []
        
        # Brand-based recommendations
        brand_count = len(analysis_results.get("brand_insights", {}))
        if brand_count > 0:
            recommendations.append(f"Leverage brand values and services from {brand_count} analyzed brand source(s)")
        
        # Competitor-based recommendations
        competitor_count = len(analysis_results.get("competitor_insights", {}))
        if competitor_count > 0:
            recommendations.append(f"Differentiate from {competitor_count} analyzed competitor(s) by highlighting unique value propositions")
        
        # Trend-based recommendations
        trend_insights = analysis_results.get("trend_insights", {})
        if trend_insights.get("trending_topics"):
            recommendations.append(f"Incorporate {len(trend_insights['trending_topics'])} identified trending topics")
        
        # File-based recommendations
        file_count = len(analysis_results.get("file_insights", []))
        if file_count > 0:
            recommendations.append(f"Utilize insights from {file_count} analyzed file(s) for content authenticity")
        
        return recommendations

# Global analyzer instance
content_analyzer = ContentAnalyzer()