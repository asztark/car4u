def apply_filters(queryset, form_data):
    if form_data.get("company_name"):
        queryset = queryset.filter(company_name__in=form_data["company_name"])

    if form_data.get("car_name"):
        queryset = queryset.filter(car_name__in=form_data["car_name"])

    if form_data.get("engine"):
        queryset = queryset.filter(engine__in=form_data["engine"])

    if form_data.get("fuel_type"):
        queryset = queryset.filter(fuel_type=form_data["fuel_type"])

    if form_data.get("seats"):
        queryset = queryset.filter(seats=form_data["seats"])

    return queryset

def build_user_vector(form_data):
    def midpoint(min_val, max_val):
        if min_val is not None and max_val is not None:
            return (min_val + max_val) / 2
        return min_val if min_val is not None else max_val

    return {
        "horsepower": midpoint(form_data.get("min_power"), form_data.get("max_power")),
        "total_speed": midpoint(form_data.get("min_speed"), form_data.get("max_speed")),
        "cars_price": midpoint(form_data.get("min_price"), form_data.get("max_price")),
    }