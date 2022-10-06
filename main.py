import os

import requests
import numpy
from dotenv import load_dotenv
from terminaltables import AsciiTable

LANGUAGES = [
    "JavaScript",
    "Java",
    "Python",
    "Ruby",
    "PHP",
    "C++",
    "C#",
    "C",
    "Go"
]

HH_URL = "https://api.hh.ru/vacancies"
SJ_URL = "https://api.superjob.ru/2.0/vacancies/"


def calculate_salary(min_salary, max_salary):
    if min_salary and max_salary:
        return (min_salary + max_salary) / 2
    elif min_salary:
        return min_salary * 1.2
    elif max_salary:
        return max_salary * 0.8


def get_hh_data_for_lang(url, lang, page=1):
    params = {
        "text": f"программист {lang}",
        "area": "1",
        "page": page,
        # "date_from": "2000-01-01",
        "period": "3",
    }

    response = requests.get(url, params=params)
    response.raise_for_status()

    return response.json()


def print_result_in_table(data, title):
    HEADINGS = [
        "Язык программирования",
        "Вакансий найдено",
        "Вакансий обработано",
        "Средняя зарплата"
    ]

    table_data = [
        HEADINGS
    ]

    for key in data:
        table_data.append([
            key,
            data[key]['vacancies_found'],
            data[key]['vacancies_processed'],
            data[key]['average_salary']
        ])

    table = AsciiTable(table_data)
    table.title = title
    print(table.table)


def predict_rub_hh_salary(vacancy):
    if vacancy['salary']:
        min_salary = vacancy['salary']['from']
        max_salary = vacancy['salary']['to']
        currency = vacancy['salary']['currency']

        if currency == "RUR":
            return calculate_salary(min_salary, max_salary)


def predict_rub_sj_salary(vacancy):
    min_salary = vacancy['payment_from']
    max_salary = vacancy['payment_to']
    currency = vacancy['currency']

    if currency == "rub":
        return calculate_salary(min_salary, max_salary)


def get_hh_analytics_data():
    langs_data = {}

    for language in LANGUAGES:

        _lang_data = get_hh_data_for_lang(HH_URL, language)

        vacancies_num = _lang_data['found']
        pages = _lang_data['pages']

        lang_vacancies = []
        for page in range(1, pages):
            _vacancies = get_hh_data_for_lang(HH_URL, language, page)['items']
            lang_vacancies.extend(_vacancies)

        salaries = []
        for vacancy in lang_vacancies:

            salary = predict_rub_hh_salary(vacancy)
            if salary:
                salaries.append(salary)

        avg_salary = int(numpy.mean(salaries))
        vacancies_studies = len(salaries)

        langs_data[language] = {
            "vacancies_found": vacancies_num,
            "vacancies_processed": vacancies_studies,
            "average_salary": avg_salary
        }
    return langs_data


def get_sj_analytics_data():
    load_dotenv()

    auth_data = {
        "X-Api-App-Id": os.environ['SJ_SECRET_KEY']
    }

    lang_data = {}

    for language in LANGUAGES:

        params = {
            "keyword": f"Программист {language}",
            "town": 4,
            "period": 0
        }

        response = requests.get(SJ_URL, headers=auth_data, params=params)
        response.raise_for_status()

        vacancies = response.json()['objects']
        vacancies_num = response.json()['total']

        salaries = []
        for vacancy in vacancies:

            salary = predict_rub_sj_salary(vacancy)
            if salary:
                salaries.append(salary)

        avg_salary = int(numpy.mean(salaries))
        vacancies_studies = len(salaries)

        lang_data[language] = {
            "vacancies_found": vacancies_num,
            "vacancies_processed": vacancies_studies,
            "average_salary": avg_salary
        }

    return lang_data


def main():
    sj_data = get_sj_analytics_data()
    hh_data = get_hh_analytics_data()

    print_result_in_table(sj_data, "SuperJob Moscow")
    print_result_in_table(hh_data, "HeadHunter Moscow")


if __name__ == "__main__":
    main()
