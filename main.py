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

SJ_WHOLE_PERIOD = 0
SJ_API_VACANCIES_LIMIT = 500


def calculate_salary(min_salary, max_salary):
    if min_salary and max_salary:
        return (min_salary + max_salary) / 2
    elif min_salary:
        return min_salary * 1.2
    elif max_salary:
        return max_salary * 0.8


def get_hh_vacanies_for_lang(url, lang, page=1):
    cities = {
        "Moscow": "1"
    }

    days = "1"

    params = {
        "text": f"программист {lang}",
        "area": cities['Moscow'],
        "page": page,
        "period": days,
    }

    response = requests.get(url, params=params)
    response.raise_for_status()

    vacancies = response.json()

    return vacancies


def print_result_in_table(salaries_analitycs, title):
    column_names = [
        "Язык программирования",
        "Вакансий найдено",
        "Вакансий обработано",
        "Средняя зарплата"
    ]

    salaries_analytics_table = [
        column_names
    ]

    for lang in salaries_analitycs:
        salaries_analytics_table.append([
            lang,
            salaries_analitycs[lang]['vacancies_found'],
            salaries_analitycs[lang]['vacancies_processed'],
            salaries_analitycs[lang]['average_salary']
        ])

    table = AsciiTable(salaries_analytics_table)
    table.title = title
    print(table.table)


def predict_rub_hh_salary(vacancy):
    if (not vacancy['salary']
        or vacancy['salary']['currency'] != "RUR"):
        return

    min_salary = vacancy['salary']['from']
    max_salary = vacancy['salary']['to']

    return calculate_salary(min_salary, max_salary)


def predict_rub_sj_salary(vacancy):
    if vacancy['currency'] != "rub":
        return

    min_salary = vacancy['payment_from']
    max_salary = vacancy['payment_to']

    return calculate_salary(min_salary, max_salary)


def analyse_hh_salaries():
    avg_salaries_by_lang = {}

    for language in LANGUAGES:

        vacancies = get_hh_vacanies_for_lang(HH_URL, language)
        vacancies_found = vacancies['found']
        pages = vacancies['pages']

        lang_vacancies = []
        for page in range(1, pages):
            _vacancies = get_hh_vacanies_for_lang(HH_URL, language, page)['items']
            lang_vacancies.extend(_vacancies)

        salaries = []
        for vacancy in lang_vacancies:

            salary = predict_rub_hh_salary(vacancy)
            if salary:
                salaries.append(salary)

        if not salaries:
            avg_salary = "No data"
        else:
            avg_salary = int(numpy.mean(salaries))

        vacancies_processed = len(salaries)

        avg_salaries_by_lang[language] = {
            "vacancies_found": vacancies_found,
            "vacancies_processed": vacancies_processed,
            "average_salary": avg_salary
        }
    return avg_salaries_by_lang


def analyse_sj_salaries(sj_secret_key):
    sj_secret_key = {
        "X-Api-App-Id": sj_secret_key
    }

    cities = {
        "Moscow": 4
    }

    vacancies_per_page = 20
    max_permited_pages = SJ_API_VACANCIES_LIMIT//vacancies_per_page

    avg_salaries_by_lang = {}

    for language in LANGUAGES:

        params = {
            "keyword": f"{language}",
            "town": cities['Moscow'],
            "period": SJ_WHOLE_PERIOD
        }

        response = requests.get(SJ_URL, headers=sj_secret_key, params=params)
        response.raise_for_status()

        vacancies_unprocessed = response.json()

        vacancies = vacancies_unprocessed['objects']
        vacancies_found = vacancies_unprocessed['total']
        pages = vacancies_unprocessed['total']//vacancies_per_page

        if pages > max_permited_pages:
            pages = max_permited_pages

        if pages:
            vacancies = []
            for page in range(pages):
                params['page'] = page
                response = requests.get(SJ_URL, headers=sj_secret_key,
                                        params=params)
                response.raise_for_status()

                vacancies_unprocessed = response.json()

                _vacancies = vacancies_unprocessed['objects']
                vacancies.extend(_vacancies)

        salaries = []
        for vacancy in vacancies:

            salary = predict_rub_sj_salary(vacancy)
            if salary:
                salaries.append(salary)

        avg_salary = int(numpy.mean(salaries))
        vacancies_processed = len(salaries)

        avg_salaries_by_lang[language] = {
            "vacancies_found": vacancies_found,
            "vacancies_processed": vacancies_processed,
            "average_salary": avg_salary
        }

    return avg_salaries_by_lang


def main():
    load_dotenv()

    sj_secret_key = os.environ['SJ_SECRET_KEY']

    sj_salaries = analyse_sj_salaries(sj_secret_key)
    hh_salaries = analyse_hh_salaries()

    print_result_in_table(sj_salaries, "SuperJob Moscow")
    print_result_in_table(hh_salaries, "HeadHunter Moscow")


if __name__ == "__main__":
    main()
