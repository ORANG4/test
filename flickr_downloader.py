#!/usr/bin/env python3
"""
Скрипт для скачивания всех фото с профиля Flickr
Ссылки на фото в нужном качестве находятся в классе class="main-photo"
"""

import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import time
import argparse
import re


def get_high_quality_flickr_image(photo_page_url, headers):
    """
    Получает URL изображения высокого качества со страницы фотографии Flickr
    
    Args:
        photo_page_url (str): URL страницы с фотографией Flickr
        headers (dict): Заголовки для HTTP-запроса
    
    Returns:
        str or None: URL изображения высокого качества или None
    """
    try:
        response = requests.get(photo_page_url, headers=headers)
        response.raise_for_status()
        
        # Попробуем найти изображение высокого качества на странице
        # Flickr часто использует различные параметры для разных размеров
        # ищем ссылки на изображения в формате https://live.staticflickr.com/{server_id}/{id}_{secret}_[a-z].jpg
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Ищем возможные ссылки на изображения высокого качества
        # На странице фотографии Flickr может быть кнопка "Download" или прямая ссылка на оригинал
        high_quality_img = None
        
        # Ищем изображения на странице
        img_tags = soup.find_all('img')
        for img in img_tags:
            src = img.get('src') or img.get('data-src')
            if src and ('staticflickr.com' in src or 'farm' in src):
                # Проверяем, не является ли это изображением высокого качества
                if re.search(r'_[bcfhkmo](_d)?\.', src):  # b, c, f, h, k, m, o - указывают на большие размеры
                    high_quality_img = src
                    break
        
        # Также проверим наличие ссылок на загрузку
        download_links = soup.find_all('a', href=re.compile(r'/photos/.*?/downloads/'))
        for link in download_links:
            download_page_url = urljoin(photo_page_url, link.get('href'))
            # На странице загрузки обычно есть прямая ссылка на оригинал
            dl_response = requests.get(download_page_url, headers=headers)
            dl_soup = BeautifulSoup(dl_response.text, 'html.parser')
            dl_img = dl_soup.find('a', {'target': '_blank'})
            if dl_img and dl_img.get('href'):
                return dl_img.get('href')
        
        # Если не нашли через поиск на странице, возвращаем найденное изображение
        if high_quality_img:
            return high_quality_img
        
        return None
    except Exception as e:
        print(f"Ошибка при получении высококачественного изображения со страницы {photo_page_url}: {str(e)}")
        return None


def download_flickr_photos(profile_url, download_dir='downloads'):
    """
    Скачивает все фотографии с профиля Flickr
    
    Args:
        profile_url (str): URL профиля Flickr
        download_dir (str): Директория для сохранения фото
    """
    
    # Создаем директорию для загрузки, если не существует
    os.makedirs(download_dir, exist_ok=True)
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        # Получаем HTML страницы профиля
        response = requests.get(profile_url, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Находим все элементы с классом "main-photo"
        photo_elements = soup.find_all(class_='main-photo')
        
        print(f"Найдено {len(photo_elements)} фото с классом 'main-photo'")
        
        downloaded_count = 0
        
        for i, element in enumerate(photo_elements, 1):
            img_url = None
            photo_page_url = None
            
            # Проверяем, является ли сам элемент изображением
            if element.name == 'img':
                img_url = element.get('src') or element.get('data-src')
            else:
                # Ищем изображение внутри элемента
                img_tag = element.find('img')
                if img_tag:
                    img_url = img_tag.get('src') or img_tag.get('data-src')
                
                # Ищем ссылку на страницу фотографии
                link_tag = element.find('a')
                if link_tag and link_tag.get('href'):
                    photo_page_url = urljoin(profile_url, link_tag.get('href'))
            
            # Если не нашли изображение напрямую, пробуем получить его со страницы фотографии
            if photo_page_url and not img_url:
                print(f"Получаем URL изображения высокого качества со страницы: {photo_page_url}")
                img_url = get_high_quality_flickr_image(photo_page_url, headers)
            
            if img_url:
                # Преобразуем относительный URL в абсолютный, если необходимо
                if not img_url.startswith('http'):
                    img_url = urljoin(profile_url, img_url)
                
                # Получаем имя файла из URL
                parsed_url = urlparse(img_url)
                filename = os.path.basename(parsed_url.path)
                
                # Если имя файла не содержит расширение, добавляем .jpg по умолчанию
                if not os.path.splitext(filename)[1]:
                    filename = f"photo_{i}.jpg"
                
                filepath = os.path.join(download_dir, filename)
                
                # Если файл уже существует, добавляем к имени номер
                counter = 1
                original_filepath = filepath
                while os.path.exists(filepath):
                    name, ext = os.path.splitext(original_filepath)
                    filepath = f"{name}_{counter}{ext}"
                    counter += 1
                
                try:
                    print(f"Скачиваем фото {i}/{len(photo_elements)}: {img_url}")
                    
                    img_response = requests.get(img_url, headers=headers)
                    img_response.raise_for_status()
                    
                    with open(filepath, 'wb') as f:
                        f.write(img_response.content)
                    
                    print(f"Фото сохранено: {filepath}")
                    downloaded_count += 1
                    
                    # Небольшая задержка между запросами, чтобы не перегружать сервер
                    time.sleep(0.5)
                    
                except Exception as e:
                    print(f"Ошибка при скачивании фото {img_url}: {str(e)}")
            else:
                print(f"Не удалось найти URL изображения в элементе {i}")
        
        print(f"\nЗавершено! Скачано {downloaded_count} фото в папку {download_dir}")
        
    except requests.RequestException as e:
        print(f"Ошибка при получении страницы: {str(e)}")
    except Exception as e:
        print(f"Произошла ошибка: {str(e)}")


def main():
    parser = argparse.ArgumentParser(description='Скачивание фото с профиля Flickr')
    parser.add_argument('url', help='URL профиля Flickr')
    parser.add_argument('-d', '--dir', default='downloads', help='Директория для загрузки фото (по умолчанию: downloads)')
    
    args = parser.parse_args()
    
    download_flickr_photos(args.url, args.dir)


if __name__ == "__main__":
    main()