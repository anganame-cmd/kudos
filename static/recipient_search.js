document.addEventListener("DOMContentLoaded", () => {
  const search = document.getElementById("recipient-search");
  const select = document.getElementById("recipient_id");
  if (!search || !select) {
    return;
  }

  const originalOptions = Array.from(select.options).map((option) =>
    option.cloneNode(true),
  );
  const placeholder = originalOptions[0];

  search.addEventListener("input", () => {
    const query = search.value.trim().toLocaleLowerCase();
    const selectedValue = select.value;
    const matchingOptions = originalOptions.slice(1).filter((option) =>
      option.textContent.trim().toLocaleLowerCase().includes(query),
    );

    select.replaceChildren(
      placeholder.cloneNode(true),
      ...matchingOptions.map((option) => option.cloneNode(true)),
    );
    if (matchingOptions.some((option) => option.value === selectedValue)) {
      select.value = selectedValue;
    } else {
      select.value = "";
    }
  });
});
